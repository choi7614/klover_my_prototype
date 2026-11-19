from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database

from app.db.models import Mail, MailAccount, User
from app.db.repositories.search import SQLSearchRepository
from app.db.repositories.search_recent import SQLRecentSearchRepository, search_metadata
from app.schemas.search import ParsedQuery, SearchOverrides, SearchScope

START = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
SCOPE = SearchScope(user_id="search-user", account_id="search-account", sync_started_at=START)


@pytest.fixture
def search_database(database):
    engine, _ = database
    search_metadata.create_all(engine)  # 명시적인 임시 스키마에만 만든다.
    with Session(engine) as session, session.begin():
        session.add_all([User(user_id="search-user"), User(user_id="other-user")])
        session.flush()
        for account, user in [
            ("search-account", "search-user"),
            ("second-account", "search-user"),
            ("other-account", "other-user"),
        ]:
            session.add(
                MailAccount(
                    account_id=account,
                    user_id=user,
                    source="fixture",
                    email=f"{account}@example.invalid",
                    sync_started_at=START,
                )
            )
        session.flush()
        for identifier, changes in [
            ("m1", {}),
            ("m2", {"received_at": START + timedelta(days=1)}),
            ("m3", {"received_at": START + timedelta(days=2)}),
            ("other-user", {"user_id": "other-user", "account_id": "other-account"}),
            ("other-account", {"account_id": "second-account"}),
            ("pre-start", {"received_at": START - timedelta(microseconds=1)}),
            ("sent", {"direction": "sent", "mailbox": "sent", "from_name": "나"}),
            ("spam", {"mailbox": "spam"}),
            ("trash", {"mailbox": "trash"}),
            ("literal", {"subject": "품의_100% 문서", "body_text": "특수문자 합성"}),
        ]:
            values = dict(
                mail_id=identifier,
                account_id="search-account",
                user_id="search-user",
                source_message_id=identifier,
                received_at=START,
                direction="received",
                mailbox="inbox",
                from_addr="budget@example.invalid",
                from_name="박지훈",
                to=[{"addr": "recipient@example.invalid", "name": "정혜원"}],
                subject="예산 문의",
                body_text="합성 예산 본문",
            )
            values.update(changes)
            session.add(Mail(**values))
    return engine


def test_postgres_search_enforces_user_account_start_and_excludes_trash(search_database):
    repository = SQLSearchRepository(search_database)
    rows = repository.candidates(SCOPE, ParsedQuery(topic="예산"))
    assert {row.mail_id for row in rows.full} == {"m1", "m2", "m3", "sent"}
    assert not rows.partial and not rows.truncated
    # 오래된/잘못된 scope라도 DB 계정의 실제 시작일과 소유자 제한을 넘지 못한다.
    broad = SCOPE.model_copy(update={"sync_started_at": START - timedelta(days=100)})
    assert repository.hydrate(broad, ["pre-start", "other-user", "other-account"]) == ()
    assert repository.hydrate(SCOPE.model_copy(update={"user_id": "other-user"}), ["m1"]) == ()


def test_korean_range_boundaries_and_full_partial_separation(search_database):
    repository = SQLSearchRepository(search_database)
    # UTC 10/1 00시는 한국 10/1 09시. 한국 10/2 00시는 UTC 10/1 15시다.
    parsed = ParsedQuery(
        topic="예산",
        filters={
            "period": {
                "start": "2026-10-01",
                "end_before": "2026-10-02",
            },
            "directions": ["received"],
        },
    )
    rows = repository.candidates(SCOPE, parsed)
    assert {row.mail_id for row in rows.full} == {"m1"}
    assert {row.mail_id for row in rows.partial} == {"m2", "m3", "sent"}


@pytest.mark.parametrize(
    "directions,kind,value,expected",
    [
        (["received"], "name", "박지훈", {"m1", "m2", "m3"}),
        (["sent"], "name", "정혜원", {"sent"}),
        (["sent"], "address", "RECIPIENT@example.invalid", {"sent"}),
        (["received"], "address", "budget@example.invalid", {"m1", "m2", "m3"}),
        (["received"], "address", "get@example.invalid", set()),
    ],
)
def test_sender_received_and_recipient_sent_conditions(
    search_database, directions, kind, value, expected
):
    rows = SQLSearchRepository(search_database).candidates(
        SCOPE,
        ParsedQuery(
            topic="예산",
            filters={"directions": directions, "counterparty": {"kind": kind, "value": value}},
        ),
    )
    assert {row.mail_id for row in rows.full} == expected


def test_keyword_wildcards_and_sql_fragments_are_literal(search_database):
    repository = SQLSearchRepository(search_database)
    literal = repository.candidates(SCOPE, ParsedQuery(topic="_100%"))
    assert [row.mail_id for row in literal.full] == ["literal"]
    attack = repository.candidates(SCOPE, ParsedQuery(topic="' OR 1=1 --"))
    assert attack.full == () and attack.partial == ()


def test_search_is_read_only_and_truncation_is_explicit(search_database):
    repository = SQLSearchRepository(search_database, candidate_limit=2)
    with Session(search_database) as session:
        before = [
            (mail.mail_id, mail.body_text, mail.is_read) for mail in session.scalars(select(Mail))
        ]
    rows = repository.candidates(SCOPE, ParsedQuery(topic="예산"))
    assert len(rows.full) == 2 and rows.truncated
    with Session(search_database) as session:
        assert before == [
            (mail.mail_id, mail.body_text, mail.is_read) for mail in session.scalars(select(Mail))
        ]


def test_recent_search_is_durable_user_account_isolated_and_deduplicated(search_database):
    repository = SQLRecentSearchRepository(search_database)
    identifier = uuid4().hex
    parsed = ParsedQuery(topic="예산")
    repository.save(SCOPE, identifier, "예산 질문", parsed, SearchOverrides(), date(2026, 11, 19))
    foreign_user = SCOPE.model_copy(update={"user_id": "other-user", "account_id": "other-account"})
    foreign_account = SCOPE.model_copy(update={"account_id": "second-account"})
    assert repository.get(foreign_user, identifier) is None
    assert repository.get(foreign_account, identifier) is None
    assert repository.recent(foreign_user) == repository.recent(foreign_account) == []
    search_database.dispose()
    assert SQLRecentSearchRepository(search_database).get(SCOPE, identifier).query == "예산 질문"
    for query in ["둘째", "셋째", "넷째", "예산 질문"]:
        repository.save(
            SCOPE, uuid4().hex, query, parsed, SearchOverrides(topic=None), date(2026, 11, 19)
        )
    recent = repository.recent(SCOPE)
    assert [item.query for item in recent] == ["예산 질문", "넷째", "셋째"]


def test_recent_save_rejects_account_owner_mismatch(search_database):
    from app.services.search_rules import SearchError

    repository = SQLRecentSearchRepository(search_database)
    with pytest.raises(SearchError):
        repository.save(
            SCOPE.model_copy(update={"user_id": "other-user"}),
            uuid4().hex,
            "합성 질문",
            ParsedQuery(topic="예산"),
            SearchOverrides(),
            date(2026, 11, 19),
        )
