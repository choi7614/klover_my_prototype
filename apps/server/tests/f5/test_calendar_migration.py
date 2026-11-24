"""0009 제안 이력은 별도 스키마에서만 왕복한다."""

import runpy
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text


def test_calendar_patch_migration_preserves_existing_data(f5db):
    root = Path(__file__).resolve().parents[4]
    installed = root / "apps/server/migrations/versions/0009_f5_calendar.py"
    if not installed.exists():
        import pytest

        pytest.skip("0009 공통 패치 미적용")
    # f5db 자체는 최신 ORM으로 만들었으므로 제안 이력의 0008→0009 경계만 별도 표에 검사한다.
    engine = f5db.engine
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE f5_calendar_credentials"))
        before = connection.execute(
            text("SELECT account_id,email FROM mail_accounts ORDER BY account_id")
        ).all()
        module = runpy.run_path(str(installed))
        for _ in range(2):
            with Operations.context(MigrationContext.configure(connection)):
                module["upgrade"]()
            assert "f5_calendar_credentials" in inspect(connection).get_table_names()
            with Operations.context(MigrationContext.configure(connection)):
                module["downgrade"]()
            assert (
                connection.execute(
                    text("SELECT account_id,email FROM mail_accounts ORDER BY account_id")
                ).all()
                == before
            )
        with Operations.context(MigrationContext.configure(connection)):
            module["upgrade"]()
