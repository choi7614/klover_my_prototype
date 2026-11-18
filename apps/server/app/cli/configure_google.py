"""사용자의 맥북에서만 JSON을 읽고 비공개 설정을 준비한다."""

import json
import os
from pathlib import Path

from cryptography.fernet import Fernet

from app.google_config import ROOT, GoogleConnectionError, read_client


def configure(source: Path, email: str, directory: Path) -> None:
    client_id, client_secret = read_client(source)
    email = email.strip().lower()
    if not email or "@" not in email or len(email) > 254:
        raise GoogleConnectionError("연결할 테스트 Gmail 주소를 확인하세요")
    # 기존 키·설정은 부분적으로라도 있으면 덮어쓰지 않는다.
    if directory.exists():
        raise GoogleConnectionError("기존 연결 설정을 보존했습니다. 변경 전 기존 키를 확인하세요")
    directory.mkdir(mode=0o700, parents=True)
    values = {
        "google-client.json": json.dumps(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost:8000/auth/google/callback"],
                }
            }
        ).encode(),
        "google-settings.json": json.dumps({"expected_email": email}).encode(),
        "token.key": Fernet.generate_key(),
    }
    for name, content in values.items():
        descriptor = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)


def main() -> None:
    try:
        source = input("다운로드한 Google JSON의 전체 경로: ").strip()
        email = input("연결할 테스트 Gmail 주소: ").strip()
        configure(Path(source).expanduser(), email, ROOT / ".local-secrets")
    except (GoogleConnectionError, OSError, EOFError):
        raise SystemExit(
            "설정을 만들지 못했습니다. JSON 경로·웹 유형·복귀 주소와 기존 설정 여부를 확인하세요."
        ) from None
    print("Google 연결 설정을 저장했습니다. JSON 내용과 암호화 키는 출력하지 않습니다.")


if __name__ == "__main__":
    main()
