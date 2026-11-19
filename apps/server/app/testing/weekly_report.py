from app.schemas.weekly_report import (
    GeneratedItem,
    GeneratedReport,
    GeneratedSection,
    ReportProfile,
)


class FixtureReportProfile:
    def __init__(self, profile: ReportProfile | None = None):
        self.profile = profile or ReportProfile(
            user_id="demo-hong",
            name="홍길동",
            title="과장",
            org="재무팀",
            report_sections=("금주 주요 업무", "진행 중인 업무", "이슈·요청사항", "차주 계획"),
            report_recipient="이수진 팀장",
            report_style="bullet",
        )

    async def get_report_profile(self, *, user_id):
        return self.profile if self.profile.user_id == user_id else None


class FixtureWeeklyGenerator:
    """모델 호출 없이 fixture 요약을 옮긴다. 업무 상태 판단·실제 AI 생성이 아니다."""

    mode = "test_double"

    def __init__(self):
        self.calls = 0

    async def generate(self, *, source, profile, style, recipient):
        self.calls += 1
        items = tuple(
            GeneratedItem(
                text=group.mails[-1].summary or group.mails[-1].body_text,
                evidence=group.mail_ids,
            )
            for group in source.groups
        )
        return GeneratedReport(
            sections=tuple(
                GeneratedSection(name=name, items=items if index == 0 else ())
                for index, name in enumerate(profile.report_sections)
            )
        )
