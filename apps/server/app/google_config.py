"""맥북 전용 연결 도구 설정. 비밀 값은 repr·오류 메시지에 포함하지 않는다."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[3]
REDIRECT_URI = "http://localhost:8000/auth/google/callback"
ORIGIN = "http://localhost:8000"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GoogleConnectionError(ValueError):
    """상세 외부 응답과 비밀 값을 담지 않는 연결 실패."""


@dataclass(frozen=True)
class GoogleSettings:
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)
    expected_email: str = field(repr=False)
    encryption_key: bytes = field(repr=False)


def read_client(path: Path) -> tuple[str, str]:
    try:
        web = json.loads(path.read_text())["web"]
        if REDIRECT_URI not in web["redirect_uris"]:
            raise ValueError
        client_id, client_secret = web["client_id"], web["client_secret"]
        if not all(isinstance(x, str) and x.strip() for x in (client_id, client_secret)):
            raise ValueError
        return client_id, client_secret
    except (OSError, ValueError, KeyError, TypeError):
        raise GoogleConnectionError("웹 클라이언트 JSON과 등록한 복귀 주소를 확인하세요") from None


def load_settings(directory: Path | None = None) -> GoogleSettings:
    directory = directory if directory is not None else ROOT / ".local-secrets"
    try:
        client_id, client_secret = read_client(directory / "google-client.json")
        email = json.loads((directory / "google-settings.json").read_text())["expected_email"]
        key = (directory / "token.key").read_bytes()
        Fernet(key)
        if not isinstance(email, str) or "@" not in email or len(email) > 254:
            raise ValueError
        return GoogleSettings(client_id, client_secret, email.strip().lower(), key)
    except (OSError, ValueError, TypeError, KeyError):
        raise GoogleConnectionError(
            "먼저 configure_google 명령으로 연결 설정을 준비하세요"
        ) from None
