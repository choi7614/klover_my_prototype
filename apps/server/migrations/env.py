"""마이그레이션은 명시적 명령으로만 실행하며 접속 문자열을 출력하지 않는다."""

from alembic import context

from app.db.config import database_engine, database_url
from app.db.f2_models import F2Base
from app.db.repositories.f5_schema import F5Base
from app.db.repositories.search_recent import search_metadata

if context.is_offline_mode():
    context.configure(
        url=database_url(),
        target_metadata=[F5Base.metadata, search_metadata, F2Base.metadata],
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = database_engine()
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=[F5Base.metadata, search_metadata, F2Base.metadata],
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
