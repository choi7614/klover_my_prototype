"""앱 읽기 API 전용 실행. 메일·인증 정보를 접근 로그에 남기지 않는다."""

import argparse

import uvicorn

from app.api.mail_read import MailAPIContext
from app.db.config import DatabaseConfigurationError, database_engine
from app.db.repositories.mail_query import MailQueryRepository
from app.db.repositories.search import SQLSearchRepository
from app.db.repositories.search_recent import SQLRecentSearchRepository
from app.google_config import GoogleConnectionError, load_settings
from app.mail_api_config import MailAPIConfigurationError, read_api_token
from app.main import create_app
from app.services.search import SearchService


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
        application.state.mail_api = MailAPIContext(
            token,
            MailQueryRepository(engine, settings.expected_email),
        )
        application.state.search_service = SearchService(
            SQLSearchRepository(engine),
            SQLRecentSearchRepository(engine),
        )
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
