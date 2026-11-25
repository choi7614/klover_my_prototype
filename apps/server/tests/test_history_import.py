"""합성 메일과 임시 PostgreSQL에서 과거 메일·체크포인트·조회 경계를 검사한다."""

import asyncio
import base64
from contextlib import contextmanager
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database
from test_postgresql_storage import seed_account

from app.api.history_import import ImportRange
from app.db.models import GoogleCredential, Mail, MailAccount
from app.db.repositories.google_connection import LOCAL_USER
from app.db.repositories.history_import import HistoryRepository
from app.db.repositories.mail_analysis import AnalysisRepository, F1ReportMailRepository
from app.db.repositories.mail_query import MailQueryRepository
from app.db.repositories.search import SQLSearchRepository
from app.schemas.search import SearchScope
from app.services.history_import import HistoryRunner


@pytest.fixture
def history(database):
    engine, _ = database
    with Session(engine) as s, s.begin():
        seed_account(s, user_id=LOCAL_USER)
        s.add(
            GoogleCredential(
                account_id="account-a", token_ciphertext="synthetic", updated_at=datetime.now(UTC)
            )
        )
    owner = SimpleNamespace(user_id=LOCAL_USER, account_id="account-a")
    return HistoryRepository(engine, owner)


class Sync:
    @contextmanager
    def credentials(self):
        yield SimpleNamespace(
            tokens={"access_token": "synthetic", "expires_at": "2099-01-01T00:00:00+00:00"}
        )


class Client:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def profile(self, access):
        return "123"

    def get(self, path, access, params):
        self.calls.append((path, params))
        if path == "/messages":
            return {"messages": [{"id": "synthetic-old"}]}
        return {
            "id": "synthetic-old",
            "threadId": "thread-old",
            "internalDate": str(int(datetime(2020, 1, 2, tzinfo=UTC).timestamp() * 1000)),
            "labelIds": ["INBOX"],
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "sender@example.invalid"},
                    {"name": "Subject", "value": "합성 과거 메일"},
                ],
                "body": {"data": base64.urlsafe_b64encode("합성 과거 본문".encode()).decode()},
            },
        }


def test_import_duplicate_query_search_report_and_cursor_preservation(history):
    client = Client()
    runner = HistoryRunner(history, Sync(), lambda: client)
    job = history.create(date(2020, 1, 1), date(2020, 1, 3))
    history.transition(job["job_id"], "resume")
    runner.run(job["job_id"])
    state = history.get(job["job_id"])
    assert state["status"] == "completed" and state["saved"] == 1
    engine = history.engine
    reader = MailQueryRepository(engine, f"{LOCAL_USER}@example.invalid")
    assert reader.list(limit=20).items[0].subject == "합성 과거 메일"
    with Session(engine) as s:
        account = s.get(MailAccount, "account-a")
        assert account.sync_cursor is None
        assert account.sync_started_at.year == 2026
        row = s.scalar(select(Mail))
        assert row.history_imported
        identifier = row.mail_id
    scope = SearchScope(
        user_id=LOCAL_USER,
        account_id="account-a",
        sync_started_at=datetime(2026, 11, 18, tzinfo=UTC),
    )
    assert SQLSearchRepository(engine).hydrate(scope, [identifier])[0].mail_id == identifier
    # SQL 조회뿐 아니라 결과 정렬·근거 답변까지 과거 메일이 도달해야 한다.
    from app.db.repositories.search_recent import SQLRecentSearchRepository
    from app.schemas.search import SearchRequest
    from app.services.search import SearchService

    class Parser:
        async def parse(self, **_):
            return {"filters": {}, "topic": "합성", "expansions": []}

    class Answerer:
        async def answer(self, *, mails, **_):
            return {"sentences": [{"mail_id": mails[0].mail_id, "quote": mails[0].body_text}]}

    result = asyncio.run(
        SearchService(
            SQLSearchRepository(engine),
            SQLRecentSearchRepository(engine),
            parser=Parser(),
            answerer=Answerer(),
        ).search(SearchRequest(query="합성 과거 메일"), scope)
    )
    assert result.results[0].mail_id == identifier
    assert result.answer.citations[0].mail_id == identifier
    mails = asyncio.run(
        F1ReportMailRepository(
            AnalysisRepository(engine, user_id=LOCAL_USER, account_id="account-a")
        ).list_received_and_sent(
            user_id=LOCAL_USER,
            start_at=datetime(2020, 1, 1, tzinfo=UTC),
            end_before=datetime(2020, 1, 4, tzinfo=UTC),
        )
    )
    assert mails[0].mail_id == identifier and mails[0].analysis_status == "pending"
    second = history.create(date(2020, 1, 1), date(2020, 1, 3))
    history.transition(second["job_id"], "resume")
    runner.run(second["job_id"])
    assert history.get(second["job_id"])["saved"] == 0
    assert history.get(second["job_id"])["skipped"] == 1


def test_pause_resume_checkpoints_and_restart_recovery(history):
    job = history.create(date(2020, 1, 1), date(2020, 1, 3))
    jid = job["job_id"]
    history.transition(jid, "resume")
    history.checkpoint(jid, source_id="already-checked")
    history.transition(jid, "pause")
    assert not history.checkpoint(jid, source_id="must-not-save")
    history.transition(jid, "resume")
    assert history.get(jid)["page_done"] == ["already-checked"]
    history.recover()
    assert history.get(jid)["status"] == "paused"
    history.transition(jid, "resume")
    history.checkpoint(jid, source_id="already-checked")
    assert history.get(jid)["processed"] == 1
    other = HistoryRepository(
        history.engine, SimpleNamespace(user_id="different", account_id="different")
    )
    assert other.get(jid) is None and not other.list()


def test_one_running_job_and_rejected_automatic_old_storage(history):
    from app.db.repositories.mail import MailRepository

    job = history.create(date(2020, 1, 1), date(2020, 1, 3))
    history.transition(job["job_id"], "resume")
    with pytest.raises(ValueError):
        history.create(date(2020, 1, 1), date(2020, 1, 3))
    with Session(history.engine) as s, s.begin():
        assert (
            MailRepository(s).store_received(
                user_id=LOCAL_USER,
                account_id="account-a",
                mail_id="old",
                source_message_id="old",
                received_at=datetime(2020, 1, 1, tzinfo=UTC),
                from_addr="test@example.invalid",
                subject="합성",
                body_text="합성",
            )
            is None
        )


def test_import_failure_can_retry_without_leaking_detail(history):
    class Broken(Client):
        def get(self, *args):
            raise RuntimeError("synthetic-private-key")

    runner = HistoryRunner(history, Sync(), Broken)
    job = history.create(date(2020, 1, 1), date(2020, 1, 3))
    history.transition(job["job_id"], "resume")
    runner.run(job["job_id"])
    assert history.get(job["job_id"])["error"] == "import_failed"
    assert "synthetic-private-key" not in str(history.list())
    history.transition(job["job_id"], "resume")
    HistoryRunner.run(
        SimpleNamespace(
            repository=history,
            sync_repository=Sync(),
            client_factory=Client,
            after_save=lambda: None,
        ),
        job["job_id"],
    )
    assert history.get(job["job_id"])["status"] == "completed"


@pytest.mark.parametrize(
    "start,end",
    [("2020-02-01", "2020-01-01"), ("2020-01-01", "2022-01-01"), ("2099-01-01", "2099-01-02")],
)
def test_range_validation(start, end):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ImportRange(start=start, end=end)


def test_stale_worker_cannot_write_after_pause_resume(history):
    job = history.create(date(2020, 1, 1), date(2020, 1, 3))
    first = history.transition(job["job_id"], "resume")["run_id"]
    history.transition(job["job_id"], "pause")
    second = history.transition(job["job_id"], "resume")["run_id"]
    assert first != second
    assert not history.checkpoint(job["job_id"], source_id="stale", expected_run_id=first)
    assert history.checkpoint(job["job_id"], source_id="current", expected_run_id=second)
    assert history.get(job["job_id"])["processed"] == 1


def test_history_http_auth_explicit_start_pause_and_private_progress(history):
    from fastapi.testclient import TestClient

    from app.api.mail_read import MailAPIContext
    from app.main import create_app

    app = create_app()
    token = "T" * 43
    app.state.mail_api = MailAPIContext(token, object())
    app.state.history_import = SimpleNamespace(
        repository=history, resume=lambda jid: history.transition(jid, "resume")
    )
    headers = {"Authorization": "Bearer " + token}
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 12345)) as http:
        assert http.get("/mail-history").status_code == 401
        assert (
            http.get(
                "/mail-history", headers={**headers, "Origin": "https://evil.invalid"}
            ).status_code
            == 403
        )
        assert http.get("/mail-history", headers=headers).json() == []
        assert (
            http.post(
                "/mail-history",
                headers=headers,
                json={"start": "2020-01-01", "end": "2020-01-03", "user_id": "other"},
            ).status_code
            == 422
        )
        response = http.post(
            "/mail-history", headers=headers, json={"start": "2020-01-01", "end": "2020-01-03"}
        )
        assert response.status_code == 201
        job = response.json()
        assert job["status"] == "running"
        assert not {"page_token", "page_done", "run_id"} & job.keys()
        assert response.headers["cache-control"] == "no-store"
        assert (
            http.post(f"/mail-history/{job['job_id']}/pause", headers=headers).json()["status"]
            == "paused"
        )
        assert http.post("/mail-history/not-owned/resume", headers=headers).status_code == 404
