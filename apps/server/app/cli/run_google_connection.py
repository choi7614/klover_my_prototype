"""맥북의 브라우저 연결 전용 서버. 인증 코드가 남지 않도록 접근 로그를 끈다."""

import uvicorn

from app.api.google_connection import create_google_app
from app.connectors.google_oauth import GoogleOAuthClient
from app.db.config import DatabaseConfigurationError, database_engine
from app.db.repositories.google_connection import GoogleConnectionRepository
from app.google_config import GoogleConnectionError, load_settings


def main() -> None:
    engine = None
    try:
        settings = load_settings()
        engine = database_engine()
        application = create_google_app(
            settings,
            GoogleOAuthClient(settings),
            GoogleConnectionRepository(engine, settings.encryption_key),
        )
        print("브라우저에서 http://localhost:8000/auth/google 을 열어 연결하세요.")
        print("연결 서버 실행 중입니다. 종료하려면 Control+C를 누르세요.")
        uvicorn.run(
            application,
            host="127.0.0.1",
            port=8000,
            access_log=False,
            proxy_headers=False,
            log_level="warning",
            workers=1,
        )
    except (GoogleConnectionError, DatabaseConfigurationError):
        raise SystemExit("Google 연결 설정과 DB 설정을 먼저 준비하세요.") from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
