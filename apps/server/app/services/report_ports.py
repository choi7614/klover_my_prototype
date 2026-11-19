"""F1 분석 결과와 F2 보고 프로필의 소유자별 읽기 포트."""

from collections.abc import Sequence
from typing import Literal, Protocol

from app.schemas.report import Identifier, MailCategory, MailEntities, ReportModel
from app.schemas.weekly_report import ReportProfile


class ReportAnalysis(ReportModel):
    mail_id: Identifier
    user_id: Identifier
    analysis_status: Literal["pending", "done", "failed"]
    category: MailCategory | None = None
    user_label: MailCategory | None = None
    summary: str | None = None
    entities: MailEntities = MailEntities()


class ReportAnalysisPort(Protocol):
    async def read_for_report(
        self, *, user_id: str, mail_ids: tuple[str, ...]
    ) -> Sequence[ReportAnalysis]: ...


class ReportProfilePort(Protocol):
    async def get_report_profile(self, *, user_id: str) -> ReportProfile | None: ...
