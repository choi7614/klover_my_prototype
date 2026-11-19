"""F4 제안 이력을 새 합성 DB 스키마에서만 적용·반복한다."""

from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database
from test_postgresql_storage import seed_account, store

from app.db.models import Mail


def test_f4_proposed_migration_preserves_mail_and_can_be_repeated(database):
    engine, _ = database
    with Session(engine) as session, session.begin():
        store(seed_account(session))
    proposal = (
        Path(__file__).resolve().parents[3] / "patches/F4/files/0006_weekly_reports.py.pending"
    )
    namespace = {}
    exec(compile(proposal.read_text(encoding="utf-8"), str(proposal), "exec"), namespace)
    assert namespace["revision"] == "0006_f4"
    assert namespace["down_revision"] == "0004_f2"
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            # 제안 합본에서도 같은 검사를 한다. 이 스키마에는 합성 데이터만 있다.
            if "weekly_reports" in inspect(connection).get_table_names():
                namespace["downgrade"]()
            namespace["upgrade"]()
            inspector = inspect(connection)
            assert {column["name"] for column in inspector.get_columns("weekly_reports")} == {
                "report_id",
                "user_id",
                "selection_key",
                "revision",
                "payload",
            }
            assert inspector.get_foreign_keys("weekly_reports")[0]["referred_table"] == "users"
            assert inspector.get_unique_constraints("weekly_reports")[0]["column_names"] == [
                "user_id",
                "selection_key",
            ]
            namespace["downgrade"]()
            assert "weekly_reports" not in inspect(connection).get_table_names()
            assert connection.scalar(select(Mail.mail_id)) == "mail-a"
            namespace["upgrade"]()
            assert connection.scalar(select(Mail.body_text)) == "실제 메일이 아닌 자동 검사 데이터"
