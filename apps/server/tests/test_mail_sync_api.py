"""POST /mails/sync 검사. 합성 저장소·클라이언트만 사용하고 실제 Gmail·DB에 접속하지 않는다."""

import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import app.api.mail_sync as mail_sync
from app.api.mail_read import MailAPIContext
from app.api.mail_sync import MailSyncContext, register_mail_sync
from app.google_config import GoogleConnectionError
from app.main import create_app

TOKEN = "A" * 43
SECRET = "합성-비밀-토큰-값"


class FakeClient:
    def __init__(self):
        self.entered = False
        self.closed = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *_):
        self.closed = True


def build(context=None, *, registered=True):
    application = create_app()
    if registered and not any(
        getattr(route, "path", None) == "/mails/sync" for route in application.routes
    ):
        register_mail_sync(application)  # main.py 등록 패치 적용 전에도 같은 경로를 검사한다.
    application.state.mail_api = MailAPIContext(TOKEN, object())
    if context is not None:
        application.state.mail_sync = context
    return TestClient(application, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 12345))


def auth():
    return {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def fake_sync(monkeypatch):
    calls = []

    def run(repository, client):
        calls.append((repository, client))
        return {"saved": 2, "skipped": 1, "mode": "history", "token_refreshed": False}

    monkeypatch.setattr(mail_sync, "synchronize", run)
    return calls


def test_sync_returns_counts_only(fake_sync):
    repository, client = object(), FakeClient()
    with build(MailSyncContext(repository, lambda: client)) as http:
        response = http.post("/mails/sync", headers=auth())
    assert response.status_code == 200
    assert response.json() == {
        "saved": 2,
        "skipped": 1,
        "mode": "history",
        "token_refreshed": False,
    }
    assert fake_sync == [(repository, client)]
    assert client.entered and client.closed
    assert response.headers["cache-control"] == "no-store"


def test_repeated_sync_reuses_duplicate_rules(monkeypatch):
    results = iter(
        [
            {"saved": 1, "skipped": 0, "mode": "initial", "token_refreshed": False},
            {"saved": 0, "skipped": 1, "mode": "history", "token_refreshed": False},
        ]
    )
    monkeypatch.setattr(mail_sync, "synchronize", lambda *_: next(results))
    with build(MailSyncContext(object(), FakeClient)) as http:
        assert http.post("/mails/sync", headers=auth()).json()["saved"] == 1
        assert http.post("/mails/sync", headers=auth()).json() == {
            "saved": 0,
            "skipped": 1,
            "mode": "history",
            "token_refreshed": False,
        }


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong"}],
)
def test_unauthenticated_sync_never_runs(fake_sync, headers):
    with build(MailSyncContext(object(), FakeClient)) as http:
        response = http.post("/mails/sync", headers=headers)
    assert response.status_code == 401
    assert fake_sync == []


@pytest.mark.parametrize(
    "extra", [{"Origin": "https://outside.invalid"}, {"X-Forwarded-For": "127.0.0.1"}]
)
def test_outside_requests_are_forbidden(fake_sync, extra):
    with build(MailSyncContext(object(), FakeClient)) as http:
        response = http.post("/mails/sync", headers={**auth(), **extra})
    assert response.status_code == 403
    assert fake_sync == []


def test_missing_sync_context_is_unavailable(fake_sync):
    with build(None) as http:
        response = http.post("/mails/sync", headers=auth())
    assert response.status_code == 503
    assert fake_sync == []


def test_sync_in_progress_is_rejected(fake_sync):
    context = MailSyncContext(object(), FakeClient)
    context.lock.acquire()
    try:
        with build(context) as http:
            response = http.post("/mails/sync", headers=auth())
    finally:
        context.lock.release()
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "sync_in_progress"
    assert fake_sync == []


def test_gmail_failure_hides_details_and_releases_lock(monkeypatch):
    def fail(*_):
        raise GoogleConnectionError(SECRET)

    monkeypatch.setattr(mail_sync, "synchronize", fail)
    context = MailSyncContext(object(), FakeClient)
    with build(context) as http:
        response = http.post("/mails/sync", headers=auth())
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "gmail_unavailable"
    assert SECRET not in response.text
    assert context.lock.acquire(blocking=False)
    context.lock.release()


def test_database_failure_is_unavailable(monkeypatch):
    def fail(*_):
        raise OperationalError("SELECT", {}, Exception(SECRET))

    monkeypatch.setattr(mail_sync, "synchronize", fail)
    with build(MailSyncContext(object(), FakeClient)) as http:
        response = http.post("/mails/sync", headers=auth())
    assert response.status_code == 503
    assert SECRET not in response.text


def test_unexpected_failure_is_generic(monkeypatch):
    def fail(*_):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(mail_sync, "synchronize", fail)
    with build(MailSyncContext(object(), FakeClient)) as http:
        response = http.post("/mails/sync", headers=auth())
    assert response.status_code == 500
    assert SECRET not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_concurrent_requests_run_once(monkeypatch):
    started, release, calls = threading.Event(), threading.Event(), []

    def slow(*_):
        calls.append(1)
        started.set()
        release.wait(5)
        return {"saved": 0, "skipped": 0, "mode": "history", "token_refreshed": False}

    monkeypatch.setattr(mail_sync, "synchronize", slow)
    context = MailSyncContext(object(), FakeClient)
    with build(context) as http:
        first = {}
        worker = threading.Thread(
            target=lambda: first.update(response=http.post("/mails/sync", headers=auth()))
        )
        worker.start()
        assert started.wait(5)
        second = http.post("/mails/sync", headers=auth())
        release.set()
        worker.join(5)
    assert second.status_code == 409
    assert first["response"].status_code == 200
    assert calls == [1]
