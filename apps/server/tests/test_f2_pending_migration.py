"""미적용 F2 마이그레이션 본문만 분리된 테스트 스키마에서 실행한다."""

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database
from test_postgresql_storage import seed_account, store

from app.db.f1_models import F1Base
from app.db.f2_models import F2Base
from app.db.models import Mail
from app.db.repositories.search_recent import search_metadata


def test_pending_migration_preserves_existing_mail_and_matches_feature_models(database):
    engine, _ = database
    with Session(engine) as session, session.begin():
        store(seed_account(session))
    source = Path(__file__).resolve().parents[3] / "patches/F2/files/0004_profile_draft.py.pending"
    namespace = {}
    exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
    assert namespace["down_revision"] == "0003_search_runs"
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            # 최신 공통 이력에는 F2가 이미 있으므로 역사적 패치의 직전 상태부터 검사한다.
            namespace["downgrade"]()
            namespace["upgrade"]()
            assert (
                compare_metadata(context, [F1Base.metadata, search_metadata, F2Base.metadata]) == []
            )
            namespace["downgrade"]()
            assert not {"profiles", "drafts", "style_learnings"} & set(
                inspect(connection).get_table_names()
            )
            assert connection.scalar(select(Mail.mail_id)) == "mail-a"
            namespace["upgrade"]()
            assert (
                compare_metadata(context, [F1Base.metadata, search_metadata, F2Base.metadata]) == []
            )
    with Session(engine) as session:
        mail = session.get(Mail, "mail-a")
        assert mail.body_text == "실제 메일이 아닌 자동 검사 데이터"
