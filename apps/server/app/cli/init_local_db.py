"""기존 파일을 덮어쓰지 않고 로컬 DB 설정을 만든다. 비밀번호는 출력하지 않는다."""

import secrets
from pathlib import Path


def main() -> None:
    target = Path(__file__).resolve().parents[4] / ".env"
    try:
        with open(target, "x", encoding="utf-8", opener=_private_file) as stream:
            stream.write(f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\nPOSTGRES_PORT=5432\n")
    except FileExistsError:
        print("기존 .env를 보존했습니다. 새 파일은 만들지 않았습니다.")
    else:
        print("개발용 .env를 생성했습니다. 비밀번호는 이 파일에서만 보관합니다.")


def _private_file(path: str, flags: int) -> int:
    import os

    return os.open(path, flags, 0o600)


if __name__ == "__main__":
    main()
