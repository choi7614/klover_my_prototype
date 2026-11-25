"""기존 F1/F2·공통 AI 조립. 운영 실행 명령에는 미적용 패치로만 등록한다."""

from app.ai.interfaces import ProvidersNotConfigured, TextGeneration
from app.ai.runtime import load_providers
from app.ai.weekly_report import SharedWeeklyReportGenerator
from app.db.repositories.mail_analysis import AnalysisRepository, F1ReportMailRepository
from app.db.repositories.profile_draft import F2Repository
from app.db.repositories.report_profile import F2ReportProfileRepository
from app.db.repositories.weekly_report import SQLWeeklyReportRepository
from app.schemas.weekly_report import ReportActor
from app.services.weekly_report import WeeklyReportError, WeeklyReportService


class WeeklyReportRuntime:
    def __init__(
        self,
        engine,
        *,
        generator: TextGeneration | None = None,
        allow_test_provider: bool = False,
        now=None,
    ):
        self.engine = engine
        self.generator = generator
        self.allow_test_provider = allow_test_provider
        self.now = now

    def for_actor(self, actor: ReportActor) -> WeeklyReportService:
        if actor.account_id is None:
            raise WeeklyReportError("session_unavailable", "연결된 메일 계정을 확인해 주세요.", 503)
        generator = self.generator
        if generator is None:
            try:
                generator, _embedding = load_providers()
            except ProvidersNotConfigured:
                generator = None
        adapter = (
            SharedWeeklyReportGenerator(generator, allow_test_provider=self.allow_test_provider)
            if generator is not None
            else None
        )
        return WeeklyReportService(
            mails=F1ReportMailRepository(
                AnalysisRepository(
                    self.engine,
                    user_id=actor.user_id,
                    account_id=actor.account_id,
                    allow_test_providers=self.allow_test_provider,
                )
            ),
            profiles=F2ReportProfileRepository(F2Repository(self.engine)),
            reports=SQLWeeklyReportRepository(self.engine),
            generator=adapter,
            now=self.now,
            allow_test_results=self.allow_test_provider,
        )
