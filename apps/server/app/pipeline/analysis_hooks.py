"""분석 완료 알림 지점(포트). 다른 기능(F5 제안 등)이 F1 분석 결과에 이어 붙는 자리다.

- F1은 분석 결과와 청크를 DB에 **확정(commit)한 뒤에만** 등록된 콜백을 부른다.
  실패(failed)는 알리지 않는다.
- 콜백 모양: ``callback(mail: AnalysisMail, result: AnalysisResult)``
  (F5 ``AnalysisScanHook``과 같다). 소유자는 ``mail.user_id``·``mail.account_id``
  (F1이 DB에서 잠가 읽은 값)이고 ``result.mail_id == mail.mail_id``다.
  일반 함수 또는 ``async def`` 모두 된다. 돌려준 값은 쓰지 않는다.
- async 콜백 시간 제한은 등록할 때 정한다(기본 ``CALLBACK_TIMEOUT``초, ``None``이면 제한 없음 —
  AI를 부르는 콜백처럼 스스로 시간 제한을 두는 경우).
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

from app.schemas.mail_analysis import AnalysisMail, AnalysisResult

logger = logging.getLogger(__name__)

CALLBACK_TIMEOUT = 10.0
_DEFAULT = object()

AnalyzedCallback = Callable[[AnalysisMail, AnalysisResult], object | Awaitable[object]]


class AnalysisHooks:
    """분석 완료 콜백 목록. 등록·해제는 어느 스레드에서 해도 된다."""

    def __init__(self):
        self._callbacks: list[tuple[AnalyzedCallback, object]] = []
        self._lock = threading.Lock()

    def register(self, callback: AnalyzedCallback, *, timeout=_DEFAULT) -> Callable[[], None]:
        """콜백을 등록하고, 등록을 해제하는 함수를 돌려준다. 같은 콜백은 한 번만 등록된다."""
        if not callable(callback):
            raise TypeError("콜백은 호출할 수 있어야 합니다")
        if (
            timeout is not _DEFAULT
            and timeout is not None
            and not (
                isinstance(timeout, int | float) and not isinstance(timeout, bool) and timeout > 0
            )
        ):
            raise ValueError("시간 제한은 양수 또는 None이어야 합니다")
        with self._lock:
            if all(existing is not callback for existing, _ in self._callbacks):
                self._callbacks.append((callback, timeout))

        def unregister():
            with self._lock:
                self._callbacks[:] = [
                    entry for entry in self._callbacks if entry[0] is not callback
                ]

        return unregister

    def __len__(self):
        with self._lock:
            return len(self._callbacks)

    async def notify(self, mail: AnalysisMail, result: AnalysisResult) -> int:
        """등록 순서대로 부른다. 실패한 콜백 수를 돌려준다(검사·관찰용)."""
        with self._lock:
            callbacks = tuple(self._callbacks)
        failed = 0
        for callback, timeout in callbacks:
            limit = CALLBACK_TIMEOUT if timeout is _DEFAULT else timeout
            try:
                value = callback(mail, result)
                if inspect.isawaitable(value):
                    if limit is None:
                        await value
                    else:
                        await asyncio.wait_for(value, limit)
            except Exception as error:  # noqa: BLE001 — 수신 측 오류가 분석 저장을 깨지 않게 한다
                failed += 1
                logger.warning(
                    "분석 완료 알림 콜백 실패: %s (%s)",
                    getattr(callback, "__qualname__", type(callback).__name__),
                    type(error).__name__,
                )
        return failed
