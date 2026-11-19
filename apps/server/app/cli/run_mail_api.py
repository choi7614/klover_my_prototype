"""앱 읽기 API 전용 실행. 메일·인증 정보를 접근 로그에 남기지 않는다."""

import argparse

import uvicorn

from app.ai.f2_port import F2Error, UnavailableDraftAI
from app.ai.f2_shared_adapter import SharedDraftAI
from app.ai.interfaces import ProvidersNotConfigured
from app.ai.runtime import load_providers
from app.ai.search_adapter import SharedQueryParser, SharedSearchAnswerer
from app.api.mail_read import MailAPIContext
from app.api.mail_sync import MailSyncContext
from app.api.profile_draft import F2Context
from app.connectors.gmail_mail import GmailMailClient
from app.db.config import DatabaseConfigurationError, database_engine
from app.db.repositories.f5 import F5Repository
from app.db.repositories.gmail_sync import GmailSyncRepository
from app.db.repositories.mail_query import MailQueryRepository
from app.db.repositories.profile_draft import F2Repository
from app.db.repositories.search import SQLSearchRepository
from app.db.repositories.search_recent import SQLRecentSearchRepository
from app.google_config import GoogleConnectionError, load_settings
from app.mail_api_config import MailAPIConfigurationError, read_api_token
from app.main import create_app
from app.pipeline.auto_analysis import build_auto_analysis
from app.services.f5 import AnalysisScanHook, F5Service
from app.services.search import SearchService
from app.services.weekly_report_runtime import WeeklyReportRuntime


def search_ai():
    """실제 공통 AI 제공자가 있을 때만 F3 해석기·답변기를 만든다. 없으면 검색은 503으로 안내한다."""
    try:
        generator, _embedding = load_providers()
        return SharedQueryParser(generator), SharedSearchAnswerer(generator)
    except ProvidersNotConfigured:
        return None, None


def draft_ai():
    """실제 공통 AI 제공자가 있을 때만 F2 답장 초안 생성을 켠다. 없으면 503으로 안내한다."""
    try:
        generator, _embedding = load_providers()
        return SharedDraftAI(generator)
    except (ProvidersNotConfigured, F2Error):
        return UnavailableDraftAI()


def main():
    parser = argparse.ArgumentParser(description="로컬 메일 조회 API 실행")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("포트는 1~65535 숫자여야 합니다")
    engine = None
    try:
        token = read_api_token()
        settings = load_settings()
        engine = database_engine()
        application = create_app()
        # F1 분류 수정(PATCH /mails/{mail_id}/category). 소유자는 기존 인증 세션에서만 정한다.
        application.state.mail_analysis_engine = engine
        mail_query = MailQueryRepository(engine, settings.expected_email)
        application.state.mail_api = MailAPIContext(token, mail_query)
        # F1 새 메일 자동 분석: 새로고침 저장 뒤 '분석 시작' 신호만 주고 응답은 기다리지 않는다.
        # AI 미설정·외부 AI면 분석하지 않고 메일은 pending으로 남는다.
        analysis_runner = build_auto_analysis(engine, mail_query.session)
        application.state.mail_analysis_runner = analysis_runner
        if analysis_runner.state == "ready":
            # 분석 완료 알림 지점에 F5 제안 만들기를 잇는다(저장 확정 뒤 hook(mail, result)).
            # 자동 분석은 로컬 AI일 때만 돌므로 F5도 같은 제공자·같은 Gmail 허용 범위를 쓴다.
            # F5 훅은 스스로 실패를 삼키고 AI 호출 시간 제한을 두므로 알림 시간 제한은 두지 않는다.
            analysis_runner.hooks.register(
                AnalysisScanHook(
                    F5Service(F5Repository(engine)), analysis_runner.providers[0], allow_gmail=True
                ),
                timeout=None,
            )
        # 앱 새로고침의 Gmail 새 메일 가져오기. CLI gmail_mail sync와 같은 저장소·수신 기능이다.
        application.state.mail_sync = MailSyncContext(
            GmailSyncRepository(engine, settings),
            lambda: GmailMailClient(settings),
            after_sync=analysis_runner.kick,
        )
        search_parser, search_answerer = search_ai()
        application.state.search_service = SearchService(
            SQLSearchRepository(engine),
            SQLRecentSearchRepository(engine),
            parser=search_parser,
            answerer=search_answerer,
        )
        # F2 답장 초안: 검색과 같은 공통 AI 제공자를 쓴다. 관련 메일 검색(related)은 아직 없다.
        application.state.profile_draft = F2Context(F2Repository(engine), ai=draft_ai())
        application.state.weekly_reports = WeeklyReportRuntime(engine)
        # 실제 Calendar transport는 별도 승인·권한 확인 전까지 차단한다.
        application.state.f5_service = F5Service(F5Repository(engine))
        print(f"메일 조회 API 실행: http://127.0.0.1:{args.port}")
        print("터미널을 켜두세요. 종료는 Control+C입니다.")
        uvicorn.run(
            application,
            host="127.0.0.1",
            port=args.port,
            access_log=False,
            proxy_headers=False,
            log_level="warning",
            workers=1,
        )
    except (MailAPIConfigurationError, GoogleConnectionError, DatabaseConfigurationError):
        raise SystemExit("기존 Google·DB 설정과 prepare_mail_api 실행 여부를 확인하세요.") from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
