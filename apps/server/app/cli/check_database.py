"""DB의 연결·마이그레이션 상태만 출력한다. 메일·주소·접속 정보는 출력하지 않는다."""

from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.db.config import DatabaseConfigurationError, database_engine


def main() -> None:
    engine = None
    try:
        engine = database_engine()
        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
            config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
            expected = ScriptDirectory.from_config(config).get_current_head()
            tables = set(inspect(connection).get_table_names())
            if (
                not expected
                or current != expected
                or not {"users", "mail_accounts", "mails"} <= tables
            ):
                raise DatabaseConfigurationError("먼저 alembic upgrade head를 실행하세요")
    except (DatabaseConfigurationError, SQLAlchemyError):
        raise SystemExit(
            "DB를 확인하지 못했습니다. 실행 상태·설정·마이그레이션을 확인하세요."
        ) from None
    finally:
        if engine is not None:
            engine.dispose()
    print('{"database":"ok","schema":"current"}')


if __name__ == "__main__":
    main()
