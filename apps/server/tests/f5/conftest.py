import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db.repositories.f5 import F5Repository
from app.db.repositories.f5_schema import F5Base
from app.db.repositories.mail import MailRepository
from app.services.f5 import F5Service

from .helpers import BODY, OTHER, OWNER, START, analysis, calendar


@pytest.fixture
def f5db():
    raw = os.environ.get("KLOVER_F5_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("KLOVER_F5_TEST_DATABASE_URL이 없어 분리 PostgreSQL 검사를 실행하지 않음")
    url = make_url(raw)
    if url.host not in {"127.0.0.1", "localhost"} or url.database != "klover_f5_test":
        pytest.fail("F5 검사는 로컬 전용 klover_f5_test DB만 허용합니다")
    admin = create_engine(url, hide_parameters=True)
    schema = "f5_test_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url.update_query_dict({"options": f"-csearch_path={schema}"}), hide_parameters=True
    )
    try:
        F5Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            repo = MailRepository(session)
            for owner in [OWNER, OTHER]:
                repo.add_user(user_id=owner.user_id)
                repo.add_account(
                    account_id=owner.account_id,
                    user_id=owner.user_id,
                    source="fixture",
                    email=owner.user_id + "@example.invalid",
                    sync_started_at=START,
                )
                repo.store_received(
                    user_id=owner.user_id,
                    account_id=owner.account_id,
                    mail_id="f5-mail" if owner == OWNER else "foreign-mail",
                    source_message_id="synthetic",
                    received_at=START,
                    from_addr="fixture@example.invalid",
                    subject="합성 전용",
                    body_text=BODY,
                )
        repository = F5Repository(engine)
        adapter, transport = calendar()
        yield SimpleNamespace(
            engine=engine,
            repository=repository,
            owner=OWNER,
            other=OTHER,
            service=F5Service(repository, adapter),
            transport=transport,
            analysis=analysis(),
        )
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
