"""Google 키와 분리한 로컬 읽기 API 토큰. 값을 출력하지 않는다."""

import os
import re
import secrets
from pathlib import Path

from app.google_config import ROOT

TOKEN_NAME = "mail-api-token"


class MailAPIConfigurationError(ValueError):
    pass


def read_api_token(directory: Path | None = None):
    directory = directory if directory is not None else ROOT / ".local-secrets"
    try:
        token = (directory / TOKEN_NAME).read_text().strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise ValueError
        return token
    except (OSError, ValueError):
        raise MailAPIConfigurationError(
            "먼저 prepare_mail_api 명령으로 로컬 API 설정을 준비하세요"
        ) from None


def prepare_api_token(directory: Path):
    if not directory.is_dir():
        raise MailAPIConfigurationError("기존 Google 연결 설정을 먼저 확인하세요")
    target = directory / TOKEN_NAME
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        read_api_token(directory)
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(secrets.token_urlsafe(32) + "\n")
    return True
