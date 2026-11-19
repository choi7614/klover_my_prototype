"""F2의 보고 프로필 읽기 계약을 F4 입력으로 변환한다."""

from starlette.concurrency import run_in_threadpool

from app.db.repositories.profile_draft import F2Repository
from app.schemas.weekly_report import ReportProfile

REPORT_SECTION_LABELS = {
    "highlights": "금주 주요 업무",
    "ongoing": "진행 중인 업무",
    "issues": "이슈·요청사항",
    "next_week": "차주 계획",
}


class F2ReportProfileRepository:
    def __init__(self, repository: F2Repository):
        self.repository = repository

    async def get_report_profile(self, *, user_id: str) -> ReportProfile | None:
        state = await run_in_threadpool(self.repository.report_profile, user_id=user_id)
        if not state.exists:
            return None
        profile = state.profile
        return ReportProfile(
            user_id=user_id,
            name=profile.name,
            title=profile.title,
            org=profile.org,
            report_sections=tuple(REPORT_SECTION_LABELS[key] for key in profile.report_sections),
            report_recipient=profile.report_recipient,
            report_style=profile.report_style,
        )
