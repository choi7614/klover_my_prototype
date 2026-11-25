"""받은편지함 분류 필터. DB 없이 API 모양과 SQL 조건을 확인한다(실제 DB 검사는 별도)."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from test_postgresql_storage import database as database

from app.api.mail_read import MailAPIContext
from app.db.repositories.mail_query import MailQueryRepository
from app.main import create_app
from app.schemas.mail_api import MailCategoryCounts, MailPage

TOKEN = "A" * 43
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


class FakeRepository:
    def __init__(self):
        self.calls = []

    def list(self, *, limit=20, cursor=None, category=None, box="inbox"):
        self.calls.append((limit, cursor, category))
        self.boxes = getattr(self, "boxes", []) + [box]
        return MailPage(items=[], next_cursor=None)

    def category_counts(self):
        return MailCategoryCounts(total=5, counts={"meeting": 2, "notice": 1})


def make_client(repository):
    application = create_app()
    application.state.mail_api = MailAPIContext(TOKEN, repository)
    return TestClient(application, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 12345))


def test_list_passes_category_to_repository():
    repository = FakeRepository()
    response = make_client(repository).get("/mails?category=meeting", headers=HEADERS)
    assert response.status_code == 200
    assert repository.calls == [(20, None, "meeting")]


def test_list_without_category_means_all_mails():
    repository = FakeRepository()
    assert make_client(repository).get("/mails", headers=HEADERS).status_code == 200
    assert repository.calls == [(20, None, None)]


@pytest.mark.parametrize(
    "query", ["category=unknown", "category=", "category=meeting&category=notice", "x=1"]
)
def test_list_rejects_bad_category_or_unknown_query(query):
    repository = FakeRepository()
    response = make_client(repository).get(f"/mails?{query}", headers=HEADERS)
    assert response.status_code == 422
    assert repository.calls == []


def test_category_counts_route_is_not_taken_by_mail_id():
    response = make_client(FakeRepository()).get("/mails/category-counts", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"total": 5, "counts": {"meeting": 2, "notice": 1}}
    assert response.headers["cache-control"] == "no-store"


def test_category_counts_requires_token():
    assert make_client(FakeRepository()).get("/mails/category-counts").status_code == 401


def compiled(query):
    return str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_category_filter_uses_user_label_before_ai_category():
    account = SimpleNamespace(
        user_id="u", account_id="a", sync_started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    repository = MailQueryRepository(engine=None, expected_email="x@example.com")
    plain = compiled(repository._received(account))
    filtered = compiled(repository._received(account, "meeting"))
    assert "f1_mail_analysis" not in plain
    assert "JOIN f1_mail_analysis" in filtered
    effective = "coalesce(f1_mail_analysis.user_label, f1_mail_analysis.category)"
    assert f"{effective} = 'meeting'" in filtered
    # 다른 사용자·계정의 분석 결과와 섞이지 않도록 소유자 조건까지 함께 묶는다.
    assert "f1_mail_analysis.user_id = mails.user_id" in filtered
    assert "f1_mail_analysis.account_id = mails.account_id" in filtered


def test_real_database_filter_and_counts_use_user_label_first(database):
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from test_mail_read_api import seeded

    from app.db.f1_models import MailAnalysisRecord
    from app.db.models import Mail

    engine, _, repository = seeded(database)
    with Session(engine) as session, session.begin():
        owner = {
            row.mail_id: (row.user_id, row.account_id)
            for row in session.scalars(select(Mail).where(Mail.mail_id.in_(["m-a", "m-b", "m-c"])))
        }
        for mail_id, ai, mine in (("m-a", "meeting", None), ("m-b", "notice", "meeting")):
            user_id, account_id = owner[mail_id]
            session.add(
                MailAnalysisRecord(
                    mail_id=mail_id,
                    user_id=user_id,
                    account_id=account_id,
                    category=ai,
                    user_label=mine,
                )
            )
    # m-b는 AI가 '공지'로 봤지만 사용자가 '회의·일정'으로 고쳐 회의에 들어간다. m-c는 분석 전이다.
    assert [m.mail_id for m in repository.list(category="meeting").items] == ["m-b", "m-a"]
    assert repository.list(category="notice").items == []
    assert len(repository.list().items) == 3
    counts = repository.category_counts()
    assert counts.total == 3 and counts.counts == {"meeting": 2}
    # 분류 필터도 페이지 넘기기(커서)가 이어진다.
    first = repository.list(category="meeting", limit=1)
    assert [m.mail_id for m in first.items] == ["m-b"] and first.next_cursor
    second = repository.list(category="meeting", limit=1, cursor=first.next_cursor)
    assert [m.mail_id for m in second.items] == ["m-a"] and second.next_cursor is None
