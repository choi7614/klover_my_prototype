from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Protocol

from app.schemas.report import ReportMail


class ReportMailRepository(Protocol):
    async def list_received_and_sent(
        self, *, user_id: str, start_at: datetime, end_before: datetime
    ) -> Sequence[ReportMail]:
        """사용자·기간으로 필터한 받은/보낸 메일을 중복 없이 반환한다."""
        ...


class InMemoryReportMailRepository:
    """명시적으로 로드한 fixture와 단위 테스트 전용. 실제 DB 어댑터가 아니다."""

    def __init__(self, mails: Iterable[ReportMail]) -> None:
        self._mails = tuple(mails)
        if len({mail.mail_id for mail in self._mails}) != len(self._mails):
            raise ValueError("메일 ID가 중복되었습니다")

    async def list_received_and_sent(
        self, *, user_id: str, start_at: datetime, end_before: datetime
    ) -> tuple[ReportMail, ...]:
        return tuple(
            sorted(
                (
                    mail
                    for mail in self._mails
                    if mail.user_id == user_id and start_at <= mail.received_at < end_before
                ),
                key=lambda mail: (mail.received_at, mail.mail_id),
            )
        )
