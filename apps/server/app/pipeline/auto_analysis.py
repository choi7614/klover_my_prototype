"""새 메일 자동 분석 작업자.

앱 새로고침(POST /mails/sync) 직후 '분석 시작' 신호만 받고 바로 돌아간다.

방식: 서버 안에 백그라운드 작업자 스레드 하나를 두고, 신호(kick)를 받으면 pending 메일이 없어질
때까지 분석한다. 요청은 신호만 주고 기다리지 않는다. 작업자는 하나라 같은 메일을 두 번 분석하지
않으며, 다른 프로세스(CLI)와는 저장소의 행 잠금(SKIP LOCKED)으로 나뉜다.

- AI 미설정: 작업자를 만들지 않는다. 메일은 'pending'으로 남는다(가짜 결과 없음).
- 외부 AI(Claude): 실제 Gmail 본문을 보내지 않는다(open-questions 14). 메일은 'pending'으로 남는다.
- 분석 실패: 저장소가 'failed'와 고정 실패 코드를 남긴다.
  retry()로 'pending'으로 되돌려 다시 분석한다.
"""

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Literal

from app.ai.interfaces import ProvidersNotConfigured, TextEmbedding, TextGeneration
from app.ai.runtime import is_external, load_providers
from app.db.repositories.mail_analysis import AnalysisRepository
from app.pipeline.analysis_hooks import AnalysisHooks
from app.pipeline.pending_analysis import process_pending

logger = logging.getLogger(__name__)

AutoAnalysisState = Literal["ready", "not_configured", "external_blocked"]


class AutoAnalysis:
    """repository_factory는 매번 현재 연결 계정의 AnalysisRepository를 만든다(소유자 고정)."""

    def __init__(
        self,
        *,
        repository_factory: Callable[[], AnalysisRepository],
        providers: tuple[TextGeneration, TextEmbedding] | None,
        hooks: AnalysisHooks | None = None,
        batch_limit: int = 20,
    ):
        if type(batch_limit) is not int or not 1 <= batch_limit <= 100:
            raise ValueError("한 번에 분석할 개수는 1~100이어야 합니다")
        self.repository_factory = repository_factory
        self.providers = providers
        self.hooks = hooks if hooks is not None else AnalysisHooks()
        self.batch_limit = batch_limit
        self._condition = threading.Condition()
        self._requested = False
        self._stopped = False
        self._thread: threading.Thread | None = None
        self._idle = threading.Event()
        self._idle.set()

    @property
    def state(self) -> AutoAnalysisState:
        if self.providers is None:
            return "not_configured"
        if is_external(self.providers[0]):
            return "external_blocked"
        return "ready"

    def kick(self) -> bool:
        """분석 시작 신호. 기다리지 않는다. 분석할 수 없는 상태면 False(메일은 pending 유지)."""
        if self.state != "ready":
            return False
        with self._condition:
            if self._stopped:
                return False
            self._requested = True
            self._idle.clear()
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._work, name="f1-auto-analysis", daemon=True
                )
                self._thread.start()
            self._condition.notify()
        return True

    def retry(
        self, repository: AnalysisRepository, mail_id: str
    ) -> Literal["queued", "not_found", "already_done", "unavailable"]:
        """실패(또는 대기) 메일을 다시 분석한다. AI를 쓸 수 없으면 상태를 바꾸지 않는다."""
        if self.state != "ready":
            return "unavailable"
        status = repository.requeue(mail_id)
        if status is None:
            return "not_found"
        if status == "done":
            return "already_done"
        self.kick()
        return "queued"

    def wait_idle(self, timeout: float | None = None) -> bool:
        """검사용: 받은 신호를 모두 처리할 때까지 기다린다."""
        return self._idle.wait(timeout)

    def close(self, timeout: float = 5.0):
        with self._condition:
            self._stopped = True
            self._condition.notify()
            thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def _work(self):
        while True:
            with self._condition:
                while not self._requested and not self._stopped:
                    self._condition.wait()
                if self._stopped:
                    self._idle.set()
                    return
                self._requested = False
            try:
                asyncio.run(self.drain())
            except Exception as error:  # noqa: BLE001 — 작업자는 죽지 않고 다음 신호를 기다린다
                # 메일 내용·DB 주소 없이 오류 종류만 남긴다. 남은 메일은 pending 그대로다.
                logger.warning("자동 분석 중단: %s", type(error).__name__)
            with self._condition:
                if not self._requested:
                    self._idle.set()

    async def drain(self) -> int:
        """pending이 없어질 때까지 분석한다. 처리한 건수를 돌려준다."""
        if self.state != "ready":
            return 0
        repository = self.repository_factory()
        llm, embeddings = self.providers
        total = 0
        while True:
            batch = await process_pending(
                repository,
                llm,
                embeddings,
                limit=self.batch_limit,
                # 로컬 제공자(외부 전송 없음)일 때만 여기까지 온다. 실제 Gmail 메일도 분석한다.
                allow_gmail=True,
                hooks=self.hooks,
            )
            total += len(batch.outcomes)
            if len(batch.outcomes) < self.batch_limit:
                return total


def build_auto_analysis(
    engine, session_reader, *, hooks: AnalysisHooks | None = None, loader=load_providers
) -> AutoAnalysis:
    """실행 명령(run_mail_api)용 조립. session_reader()는 현재 연결 계정(user_id·account_id)을 준다.

    AI 미설정이면 providers=None인 작업자를 돌려준다(state=not_configured, 신호를 받아도 무시).
    다른 기능은 ``runner.hooks.register(callback)``로 분석 완료 알림 지점에 이어 붙는다.
    """
    try:
        providers = loader()
    except ProvidersNotConfigured:
        providers = None

    def repository_factory():
        scope = session_reader()
        return AnalysisRepository(engine, user_id=scope.user_id, account_id=scope.account_id)

    return AutoAnalysis(repository_factory=repository_factory, providers=providers, hooks=hooks)
