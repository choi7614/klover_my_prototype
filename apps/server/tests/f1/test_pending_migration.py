"""F1 0007 제안 이력을 분리 테스트 DB의 일회용 스키마에서만 적용·되돌리기·재적용한다."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.db.f1_models import F1Base
from app.db.f2_models import F2Base
from app.db.repositories.search_recent import search_metadata

ROOT = Path(__file__).resolve().parents[4]
PENDING = ROOT / "patches/F1/files/0007_f1_analysis.py.pending"
INSTALLED = ROOT / "apps/server/migrations/versions/0007_f1_analysis.py"
F1_TABLES = {"f1_mail_analysis", "f1_mail_chunks", "f1_category_feedback"}


@pytest.fixture
def head_schema(monkeypatch):
    raw = os.environ.get("KLOVER_F1_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("KLOVER_F1_TEST_DATABASE_URL이 없어 분리 PostgreSQL 검사를 실행하지 않음")
    url = make_url(raw)
    if not url.database.endswith("_test"):
        pytest.fail("F1 검사는 _test로 끝나는 분리 DB만 허용합니다")
    schema = "f1_mig_" + uuid4().hex
    admin = create_engine(url, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = url.update_query_dict({"options": f"-csearch_path={schema},public"})
    monkeypatch.setenv("DATABASE_URL", scoped.render_as_string(hide_password=False))
    config = Config(str(ROOT / "apps/server/alembic.ini"))
    engine = create_engine(scoped, hide_parameters=True)
    try:
        yield engine, config
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def pending_module():
    namespace = {}
    exec(compile(PENDING.read_text(encoding="utf-8"), str(PENDING), "exec"), namespace)
    return namespace


def all_metadata():
    # 이 검사는 0007 자체를 왕복한다. 0008의 추가물만 제외한 스냅샷과 비교한다.
    from sqlalchemy import MetaData

    target = MetaData()
    for table in F1Base.metadata.tables.values():
        if table.name == "history_import_jobs":
            continue
        copied = table.to_metadata(target)
        if table.name == "mails" and "history_imported" in copied.c:
            copied._columns.remove(copied.c.history_imported)
    return [target, search_metadata, F2Base.metadata]


def test_pending_revision_follows_reserved_number():
    module = pending_module()
    assert module["revision"] == "0007_f1" and module["down_revision"] == "0006_f4"
    if INSTALLED.exists():
        # 통합 후에는 적용된 이력과 제안 파일이 같아야 한다.
        assert INSTALLED.read_text(encoding="utf-8") == PENDING.read_text(encoding="utf-8")


def test_pending_migration_matches_models_and_round_trips(head_schema):
    engine, config = head_schema
    module = pending_module()
    command.upgrade(config, "0006_f4")
    for _round in range(2):
        with engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                module["upgrade"]()
        with engine.connect() as connection:
            assert F1_TABLES <= set(inspect(connection).get_table_names())
            assert compare_metadata(MigrationContext.configure(connection), all_metadata()) == []
        with engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                module["downgrade"]()
        with engine.connect() as connection:
            inspector = inspect(connection)
            assert not F1_TABLES & set(inspector.get_table_names())
            # 기존 메일 테이블과 F5의 소유 유일 제약은 그대로 남는다.
            assert "uq_mail_f5_owner" in {
                item["name"] for item in inspector.get_unique_constraints("mails")
            }


def test_pending_migration_keeps_existing_mail_rows(head_schema):
    engine, config = head_schema
    command.upgrade(config, "0006_f4")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users(user_id) VALUES ('mig-user')"))
        connection.execute(
            text(
                "INSERT INTO mail_accounts(account_id,user_id,source,email,sync_started_at) "
                "VALUES ('mig-account','mig-user','fixture','mig@example.invalid',now())"
            )
        )
        connection.execute(
            text(
                "INSERT INTO mails(mail_id,account_id,user_id,source_message_id,direction,"
                "from_addr,subject,body_text,received_at) VALUES ('mig-mail','mig-account',"
                "'mig-user','src','received','a@example.invalid','합성','합성 본문',now())"
            )
        )
    module = pending_module()
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            module["upgrade"]()
            module["downgrade"]()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT body_text FROM mails")) == "합성 본문"
