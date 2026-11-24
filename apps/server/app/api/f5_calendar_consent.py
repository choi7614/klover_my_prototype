"""Calendar만 저장하는 추가 동의 화면. 기존 Google 브라우저 연결 보안 재사용."""

from functools import partial

from app.api.google_connection import create_google_app
from app.connectors.google_calendar import SCOPES
from app.connectors.google_oauth import GoogleOAuthClient, authorization_url
from app.google_config import GMAIL_SCOPE


def consent_app(settings, repository, transport=None):
    scopes = SCOPES | {GMAIL_SCOPE}
    return create_google_app(
        settings,
        GoogleOAuthClient(settings, transport, scopes=scopes),
        repository,
        start_url=partial(authorization_url, scopes=scopes),
        message=f"{settings.expected_email} 계정의 Calendar 추가 권한을 요청합니다. "
        "소유 캘린더 일정 쓰기·목록·겹침 조회에 사용합니다. "
        "기존 Gmail 연결을 유지하며 연결만으로 일정은 등록하지 않습니다.",
    )
