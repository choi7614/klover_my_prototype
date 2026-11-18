"""DB 설정은 필요할 때만 읽는다. /health는 DB 설정 없이 계속 실행된다."""

import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class DatabaseConfigurationError(ValueError):
    pass


def database_url() -> URL:
    values = {**dotenv_values(Path(__file__).resolve().parents[4] / ".env"), **os.environ}
    if raw := values.get("DATABASE_URL"):
        try:
            url = make_url(raw)
            if url.get_backend_name() != "postgresql":
                raise ValueError
            return url.set(drivername="postgresql+psycopg")
        except (ArgumentError, ValueError, TypeError) as error:
            raise DatabaseConfigurationError(
                "DATABASE_URL에 PostgreSQL 주소를 설정하세요"
            ) from error
    password = values.get("POSTGRES_PASSWORD")
    if not password or password == "replace-with-local-random-password":
        raise DatabaseConfigurationError("먼저 개발용 .env를 생성하세요")
    try:
        port = int(values.get("POSTGRES_PORT", "5432"))
        if not 1 <= port <= 65535:
            raise ValueError
    except (ValueError, TypeError) as error:
        raise DatabaseConfigurationError("POSTGRES_PORT는 1~65535 숫자여야 합니다") from error
    return URL.create(
        "postgresql+psycopg",
        username="klover",
        password=password,
        host="127.0.0.1",
        port=port,
        database="klover",
    )


def database_engine(url: URL | None = None) -> Engine:
    return create_engine(
        url if url is not None else database_url(),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )
