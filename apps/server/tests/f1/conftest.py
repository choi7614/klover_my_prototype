"""새 전용 테스트 DB의 일회용 스키마에만 공통 이력·미적용 F1 패치를 검증한다."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


@pytest.fixture
def f1_database(monkeypatch):
    raw = os.environ.get("KLOVER_F1_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("KLOVER_F1_TEST_DATABASE_URL이 없어 분리 PostgreSQL 검사를 실행하지 않음")
    url = make_url(raw)
    if not url.database.endswith("_test"):
        pytest.fail("F1 검사는 _test로 끝나는 분리 DB만 허용합니다")
    schema = "f1_test_" + uuid4().hex
    admin = create_engine(url, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = url.update_query_dict({"options": f"-csearch_path={schema},public"})
    monkeypatch.setenv("DATABASE_URL", scoped.render_as_string(hide_password=False))
    server = Path(__file__).resolve().parents[2]
    config = Config(str(server / "alembic.ini"))
    engine = create_engine(scoped, hide_parameters=True)
    try:
        command.upgrade(config, "head")
        patch = server.parents[1] / "integration/F1-mail-analysis/001_storage.sql"
        with engine.begin() as connection:
            for statement in patch.read_text().split(";"):
                if statement.strip():
                    connection.exec_driver_sql(statement)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
