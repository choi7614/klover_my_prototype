from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.mail_analysis import register_mail_analysis
from app.api.mail_read import MailAPIContext
from app.main import create_app
from tests.f1.test_storage import seed


@pytest.fixture
def client(f1_database):
    seed(f1_database)
    # 운영 등록 전후 모두 같은 경로 하나만 쓰도록 등록 함수로 테스트 DB 엔진을 넣는다.
    application = create_app()
    register_mail_analysis(application, f1_database)
    application.state.mail_api = MailAPIContext(
        token="synthetic-api-token",
        repository=SimpleNamespace(
            session=lambda: SimpleNamespace(user_id="f1-user-a", account_id="f1-account-a")
        ),
    )
    with TestClient(
        application,
        base_url="http://localhost",
        client=("127.0.0.1", 43210),
        headers={"Authorization": "Bearer synthetic-api-token"},
    ) as session:
        yield session


def test_category_router_commits_label_feedback_and_private_headers(client, f1_database):
    response = client.patch("/mails/f1-001/category", json={"category": "report_share"})
    assert response.status_code == 200
    assert response.json() == {
        "mail_id": "f1-001",
        "user_label": "report_share",
        "effective_category": "report_share",
    }
    assert response.headers["cache-control"] == "no-store"
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT user_label FROM f1_mail_analysis")) == "report_share"
        assert connection.scalar(text("SELECT count(*) FROM f1_category_feedback")) == 1


def test_unauthorized_and_external_origin_do_not_mutate(client, f1_database):
    for headers, code in [
        ({"Authorization": "Bearer wrong"}, 401),
        ({"Origin": "https://example.invalid"}, 403),
        ({"X-Forwarded-For": "192.0.2.1"}, 403),
    ]:
        response = client.patch(
            "/mails/f1-001/category", json={"category": "notice"}, headers=headers
        )
        assert response.status_code == code
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_analysis")) == 0


def test_other_owner_and_nonexistent_id_have_same_404(client, f1_database):
    with f1_database.begin() as connection:
        connection.execute(text("INSERT INTO users(user_id) VALUES ('other-user')"))
        connection.execute(
            text("""
            INSERT INTO mail_accounts(account_id,user_id,source,email,sync_started_at)
            VALUES ('other-account','other-user','fixture','other@example.invalid',:start)
        """),
            {"start": datetime.fromisoformat("2026-01-01T00:00:00+00:00")},
        )
        connection.execute(
            text("""
            INSERT INTO mails(mail_id,account_id,user_id,source_message_id,direction,
                              from_addr,subject,body_text,received_at)
            VALUES ('other-mail','other-account','other-user','source-other','received',
                    'sender@example.invalid','합성','합성',:start)
        """),
            {"start": datetime.fromisoformat("2026-11-18T00:00:00+00:00")},
        )
    for mail_id in ("other-mail", "missing-mail"):
        assert (
            client.patch(f"/mails/{mail_id}/category", json={"category": "notice"}).status_code
            == 404
        )


def test_owner_injection_and_custom_categories_are_rejected(client):
    for payload in ({"category": "custom"}, {"category": "notice", "user_id": "other"}):
        assert client.patch("/mails/f1-001/category", json=payload).status_code == 422


def test_operational_app_does_not_register_f1_routes():
    schema = create_app().openapi()
    assert "/mails/{mail_id}/category" not in schema["paths"]


def registered_client(engine=None):
    application = create_app()
    register_mail_analysis(application, engine)
    register_mail_analysis(application, engine)  # 두 번 불러도 경로는 한 번만 등록된다.
    application.state.mail_api = MailAPIContext(
        token="synthetic-api-token",
        repository=SimpleNamespace(
            session=lambda: SimpleNamespace(user_id="f1-user-a", account_id="f1-account-a")
        ),
    )
    return TestClient(
        application,
        base_url="http://localhost",
        client=("127.0.0.1", 43210),
        headers={"Authorization": "Bearer synthetic-api-token"},
    )


def test_registration_without_engine_answers_503_and_writes_nothing():
    with registered_client() as session:
        response = session.patch("/mails/f1-001/category", json={"category": "notice"})
        assert response.status_code == 503
        assert response.headers["cache-control"] == "no-store"
        paths = session.app.openapi()["paths"]
        assert list(paths["/mails/{mail_id}/category"]) == ["patch"]


def test_registration_with_engine_updates_category(f1_database):
    seed(f1_database)
    with registered_client(f1_database) as session:
        response = session.patch("/mails/f1-001/category", json={"category": "notice"})
        assert response.status_code == 200 and response.json()["user_label"] == "notice"
        assert session.patch("/mails/f1-001/category", json={}).status_code == 422
