"""명시적으로 지정한 테스트 DB 안의 임시 스키마만 만들고 제거한다."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.f1_models import F1Base
from app.db.f2_models import F2Base
from app.db.models import Mail
from app.db.repositories.mail import MailRepository
from app.db.repositories.search_recent import search_metadata

START = datetime(2026, 11, 18, 0, 0, tzinfo=UTC)


@pytest.fixture
def database(monkeypatch):
    raw = os.environ.get("KLOVER_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("KLOVER_TEST_DATABASE_URL이 없어 실제 PostgreSQL 검사를 실행하지 않음")
    schema = "klover_test_" + uuid4().hex
    admin = create_engine(raw, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(raw).update_query_dict({"options": f"-csearch_path={schema}"})
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    engine = create_engine(url, hide_parameters=True)
    try:
        command.upgrade(config, "head")
        yield engine, config
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def seed_account(session, *, user_id="user-a", account_id="account-a"):
    repository = MailRepository(session)
    repository.add_user(user_id=user_id)
    repository.add_account(
        account_id=account_id,
        user_id=user_id,
        source="gmail",
        email=f"{user_id}@example.invalid",
        sync_started_at=START,
    )
    return repository


def store(repository, **overrides):
    values = dict(
        user_id="user-a",
        account_id="account-a",
        mail_id="mail-a",
        source_message_id="source-a",
        received_at=START,
        from_addr="sender@example.invalid",
        subject="합성 테스트 제목",
        body_text="실제 메일이 아닌 자동 검사 데이터",
        to=[{"addr": "user-a@example.invalid"}],
    )
    values.update(overrides)
    return repository.store_received(**values)


def test_migration_repeat_and_model_match(database):
    engine, config = database
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            compare_metadata(
                MigrationContext.configure(connection),
                [F1Base.metadata, search_metadata, F2Base.metadata],
            )
            == []
        )
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            compare_metadata(
                MigrationContext.configure(connection),
                [F1Base.metadata, search_metadata, F2Base.metadata],
            )
            == []
        )


def test_mail_survives_session_and_connection_recreation(database):
    engine, _ = database
    with Session(engine) as session, session.begin():
        repository = seed_account(session)
        assert store(repository) == "mail-a"
    engine.dispose()
    with Session(engine) as session:
        mails = MailRepository(session).list_received(user_id="user-a")
        assert len(mails) == 1
        assert mails[0].subject == "합성 테스트 제목"
        assert mails[0].to == [{"addr": "user-a@example.invalid"}]
        assert mails[0].received_at == START
        assert mails[0].analysis_status == "pending"


def test_repeated_source_message_keeps_existing_id_and_content(database):
    engine, _ = database
    with Session(engine) as session, session.begin():
        repository = seed_account(session)
        store(repository)
        assert store(repository, mail_id="retry-id", subject="재시도 제목") == "mail-a"
        assert len(repository.list_received(user_id="user-a")) == 1
        assert repository.list_received(user_id="user-a")[0].subject == "합성 테스트 제목"


def test_history_boundary_and_user_isolation(database):
    engine, _ = database
    with Session(engine) as session, session.begin():
        repository = seed_account(session)
        seed_account(session, user_id="user-b", account_id="account-b")
        assert store(repository, received_at=START - timedelta(microseconds=1)) is None
        assert store(repository) == "mail-a"
        assert repository.list_received(user_id="user-b") == []
        with pytest.raises(ValueError, match="아카운트"):
            store(repository, user_id="user-b")
        assert (
            store(
                repository,
                user_id="user-b",
                account_id="account-b",
                mail_id="mail-b",
            )
            == "mail-b"
        )


def test_database_rejects_mail_with_wrong_account_owner(database):
    engine, _ = database
    with Session(engine) as session, session.begin():
        seed_account(session)
        seed_account(session, user_id="user-b", account_id="account-b")
    with Session(engine) as session, pytest.raises(IntegrityError):
        session.add(
            Mail(
                mail_id="wrong-owner",
                account_id="account-a",
                user_id="user-b",
                source_message_id="invalid-owner",
                received_at=START,
                direction="received",
                from_addr="sender@example.invalid",
                subject="합성",
                body_text="합성",
            )
        )
        session.commit()


def test_naive_timestamp_rejected_and_transaction_rollback(database):
    engine, _ = database
    with Session(engine) as session, session.begin():
        repository = seed_account(session)
        with pytest.raises(ValueError, match="시간대"):
            store(repository, received_at=START.replace(tzinfo=None))
    with Session(engine) as session:
        store(MailRepository(session))
        session.rollback()
    with Session(engine) as session:
        assert MailRepository(session).list_received(user_id="user-a") == []


def test_database_cli_status_contains_no_user_data(database, capsys):
    from app.cli.check_database import main

    main()
    assert capsys.readouterr().out.strip() == '{"database":"ok","schema":"current"}'
