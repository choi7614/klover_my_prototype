from typing import Literal, Protocol

from app.schemas.report import WeeklyReportInput
from app.schemas.weekly_report import GeneratedReport, ReportProfile


class WeeklyReportGenerator(Protocol):
    mode: Literal["test_double", "ai"]

    async def generate(
        self, *, source: WeeklyReportInput, profile: ReportProfile, style: str, recipient: str
    ) -> GeneratedReport:
        """F1 공통 인터페이스가 생기면 이 경계 안에서 연결한다. 직접 외부 호출은 금지한다."""
        ...
