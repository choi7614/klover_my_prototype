"""명시적으로 실행하는 Calendar 추가 동의 도구. Gmail 설정/키/계정은 재사용한다."""

from functools import partial

import uvicorn

from app.api.google_connection import create_google_app
from app.connectors.google_calendar import SCOPES
from app.connectors.google_oauth import GoogleOAuthClient, authorization_url
from app.db.config import database_engine
from app.db.repositories.f5_calendar import CalendarConnectionRepository
from app.google_config import GMAIL_SCOPE, load_settings


def main():
    settings = load_settings()
    engine = database_engine()
    try:
        scopes = SCOPES | {GMAIL_SCOPE}
        app = create_google_app(
            settings,
            GoogleOAuthClient(settings, scopes=scopes),
            CalendarConnectionRepository(engine, settings.encryption_key),
            start_url=partial(authorization_url, scopes=scopes),
            message=f"{settings.expected_email} 계정의 Calendar 추가 권한을 요청합니다. "
            "이 연결만으로 일정은 등록되지 않습니다. Gmail 연결은 유지합니다.",
        )
        print("업무 서버를 잠시 멈추고 http://localhost:8000/auth/google 에서 추가 동의하세요.")
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            access_log=False,
            proxy_headers=False,
            log_level="warning",
            workers=1,
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
