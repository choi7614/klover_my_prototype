"""분석 완료 알림 지점(포트). 다른 기능(F5 제안 등)이 F1 분석 결과에 이어 붙는 자리다.

- F1은 분석 결과와 청크를 DB에 **확정(commit)한 뒤에만** 등록된 콜백을 부른다.
  실패(failed)는 알리지 않는다.
- 콜백 시그니처: ``callback(owner: AnalysisOwner, mail_id: str, result: AnalysisResult)``.
  일반 함수 또는 ``async def`` 모두 된다. async 콜백은 ``CALLBACK_TIMEOUT``초 안에 끝나야 한다.
- 콜백의 오류·시간 초과는 기록만 하고 삼킨다. 이미 저장된 분석 상태(done)를 바꾸지 않고
  다음 콜백·다음 메일 처리도 계속한다. 로그에는 콜백 이름과 오류 종류만 남긴다(메일 내용 없음).
- 이 알림은 서버 메모리 안의 즉시 알림이다(전달 보장·재전송 없음). 서버가 알림 직전에 꺼지면
  해당 메일의 알림은 사라진다. 놓친 결과는 수신 측이 F1 저장소(done 메일)를 다시 읽어 보완한다.
"""

import asyncio
import inspect
import logging
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.schemas.mail_analysis import AnalysisResult

logger = logging.getLogger(__name__)

CALLBACK_TIMEOUT = 10.0


@dataclass(frozen=True)
class AnalysisOwner:
    """분석한 메일의 소유자. 콜백은 이 범위 밖의 데이터를 읽거나 쓰지 않는다."""

    user_id: str
    account_id: str


AnalyzedCallback = Callable[[AnalysisOwner, str, AnalysisResult], None | Awaitable[None]]


class AnalysisHooks:
    """분석 완료 콜백 목록. 등록·해제는 어느 스레드에서 해도 된다."""

    def __init__(self):
        self._callbacks: list[AnalyzedCallback] = []
        self._lock = threading.Lock()

    def register(self, callback: AnalyzedCallback) -> Callable[[], None]:
        """콜백을 등록하고, 등록을 해제하는 함수를 돌려준다. 같은 콜백은 한 번만 등록된다."""
        if not callable(callback):
            raise TypeError("콜백은 호출할 수 있어야 합니다")
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

        def unregister():
            with self._lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)

        return unregister

    def __len__(self):
        with self._lock:
            return len(self._callbacks)

    async def notify(self, owner: AnalysisOwner, mail_id: str, result: AnalysisResult) -> int:
        """등록 순서대로 부른다. 실패한 콜백 수를 돌려준다(검사·관찰용)."""
        with self._lock:
            callbacks = tuple(self._callbacks)
        failed = 0
        for callback in callbacks:
            try:
                value = callback(owner, mail_id, result)
                if inspect.isawaitable(value):
                    await asyncio.wait_for(value, CALLBACK_TIMEOUT)
            except Exception as error:  # noqa: BLE001 — 수신 측 오류가 분석 저장을 깨지 않게 한다
                failed += 1
                logger.warning(
                    "분석 완료 알림 콜백 실패: %s (%s)",
                    getattr(callback, "__qualname__", type(callback).__name__),
                    type(error).__name__,
                )
        return failed
