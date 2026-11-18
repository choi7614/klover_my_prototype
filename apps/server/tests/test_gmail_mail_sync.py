import base64
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database

from app.connectors.gmail_mail import GmailMailClient
from app.connectors.gmail_message import parse_message
from app.db.models import GoogleCredential, Mail, MailAccount
from app.db.repositories.gmail_sync import GmailSyncRepository
from app.db.repositories.google_connection import GoogleConnectionRepository
from app.google_config import GMAIL_SCOPE, GoogleConnectionError, GoogleSettings
from app.services.gmail_sync import synchronize

EMAIL = "sync@example.invalid"
START = datetime(2026, 11, 19, 10, 0, 0, 123000, tzinfo=UTC)


def message(identifier="m1", when=START, *, html=False):
    body = "<p>합성 &amp; 본문</p><script>hidden</script>" if html else "합성 전용 본문"
    return {
        "id": identifier,
        "threadId": "thread1",
        "internalDate": str(int(when.timestamp() * 1000)),
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "mimeType": "text/html" if html else "text/plain",
            "headers": [
                {"name": "From", "value": "테스트 <sender@example.invalid>"},
                {"name": "To", "value": "수신자 <sync@example.invalid>"},
                {"name": "Cc", "value": "copy@example.invalid"},
                {"name": "Subject", "value": "=?UTF-8?B?7ZWp7ISx?="},
            ],
            "body": {"data": base64.urlsafe_b64encode(body.encode()).decode().rstrip("=")},
        },
    }


class GmailResponses:
    def __init__(self, messages=None):
        self.messages = messages or {"m1": message()}
        self.calls = []
        self.history_id = "200"
        self.pages = {None: {"messages": [{"id": x} for x in self.messages]}}
        self.history = {
            None: {"history": [{"messagesAdded": [{"message": {"id": x}} for x in self.messages]}]}
        }
        self.expired_history = False
        self.failed_ids = set()
        self.fail_refresh = False
        self.rotate_refresh = False
        self.reject_old_access = False
        self.email = EMAIL

    def __call__(self, request):
        self.calls.append(request)
        path, params = request.url.path, request.url.params
        if path == "/token":
            assert request.method == "POST"
            if self.fail_refresh:
                return httpx.Response(400, json={"error": "synthetic-private-refresh-error"})
            payload = {"access_token": "new-access", "expires_in": 3600, "token_type": "Bearer"}
            if self.rotate_refresh:
                payload["refresh_token"] = "rotated-refresh"
            return httpx.Response(200, json=payload)
        assert request.method == "GET"
        if self.reject_old_access and request.headers["authorization"] == "Bearer old-access":
            return httpx.Response(401)
        if path.endswith("/profile"):
            return httpx.Response(
                200, json={"emailAddress": self.email, "historyId": self.history_id}
            )
        if path.endswith("/history"):
            if self.expired_history:
                return httpx.Response(404)
            return httpx.Response(200, json=self.history[params.get("pageToken")])
        if path.endswith("/messages"):
            assert params["labelIds"] == "INBOX"
            assert params["q"] == f"after:{int(START.timestamp()) - 1}"
            return httpx.Response(200, json=self.pages[params.get("pageToken")])
        identifier = path.rsplit("/", 1)[-1]
        if identifier in self.failed_ids:
            return httpx.Response(500, json={"body": "synthetic-private-failure"})
        if identifier not in self.messages:
            return httpx.Response(404)
        data = self.messages[identifier]
        if params["format"] == "metadata":
            data = {k: v for k, v in data.items() if k in {"id", "labelIds", "internalDate"}}
        return httpx.Response(200, json=data)


def connected(database, *, expired=False, cursor=None):
    engine, _ = database
    settings = GoogleSettings("synthetic-client", "synthetic-secret", EMAIL, Fernet.generate_key())
    GoogleConnectionRepository(engine, settings.encryption_key).save(
        EMAIL,
        {
            "access_token": "old-access",
            "refresh_token": "old-refresh",
            "expires_in": 3600,
            "scope": GMAIL_SCOPE,
        },
    )
    with Session(engine) as session, session.begin():
        account = session.scalar(select(MailAccount))
        account.sync_started_at, account.sync_cursor = START, cursor
        account_id = account.account_id
        if expired:
            row = session.scalar(select(GoogleCredential))
            payload = json.loads(
                Fernet(settings.encryption_key).decrypt(row.token_ciphertext.encode())
            )
            payload["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
            row.token_ciphertext = (
                Fernet(settings.encryption_key).encrypt(json.dumps(payload).encode()).decode()
            )
    return engine, settings, GmailSyncRepository(engine, settings), account_id


def sync(repository, settings, responses):
    with GmailMailClient(settings, httpx.MockTransport(responses)) as client:
        return synchronize(repository, client)


def body_requests(responses):
    return [
        r.url.path.rsplit("/", 1)[-1]
        for r in responses.calls
        if r.url.params.get("format") == "full"
    ]


def decrypted(engine, settings):
    with Session(engine) as session:
        ciphertext = session.scalar(select(GoogleCredential.token_ciphertext))
        assert "access" not in ciphertext and "refresh" not in ciphertext
        return json.loads(Fernet(settings.encryption_key).decrypt(ciphertext.encode()))


def test_initial_pagination_boundary_and_stored_fields(database, monkeypatch, capsys):
    engine, settings, repository, account_id = connected(database)
    responses = GmailResponses(
        {
            "old": message("old", START - timedelta(milliseconds=1)),
            "m1": message(),
            "m2": message("m2", START + timedelta(seconds=1)),
        }
    )
    responses.pages = {
        None: {"messages": [{"id": "old"}, {"id": "m1"}], "nextPageToken": "next"},
        "next": {"messages": [{"id": "m1"}, {"id": "m2"}]},
    }
    result = sync(repository, settings, responses)
    assert result["saved"] == 2 and result["skipped"] == 1 and result["mode"] == "initial"
    assert set(body_requests(responses)) == {"m1", "m2"}
    with Session(engine) as session:
        rows = list(session.scalars(select(Mail)))
        assert len(rows) == 2 and all(row.account_id == account_id for row in rows)
        row = next(x for x in rows if x.source_message_id == "m1")
        assert row.received_at == START and row.subject == "합성"
        assert row.from_addr == "sender@example.invalid" and row.from_name == "테스트"
        assert row.cc == [{"addr": "copy@example.invalid", "name": ""}]
        assert row.body_text == "합성 전용 본문" and not row.is_read
        assert row.analysis_status == "pending"
        account = session.get(MailAccount, account_id)
        assert account.sync_cursor == "200" and account.sync_started_at == START
    assert set(repository.list_received()[0]) == {"mail_id", "received_at", "analysis_status"}
    from app.cli import gmail_mail

    monkeypatch.setattr(gmail_mail, "load_settings", lambda: settings)
    monkeypatch.setattr(gmail_mail, "database_engine", lambda: engine)
    monkeypatch.setattr("sys.argv", ["gmail_mail", "list"])
    gmail_mail.main()
    output = capsys.readouterr().out
    assert json.loads(output)["count"] == 2
    for private in ["합성", "sender@example.invalid", "old-access", "old-refresh"]:
        assert private not in output


def test_history_replay_deduplicates_and_preserves_existing_mail(database):
    engine, settings, repository, _ = connected(database)
    responses = GmailResponses()
    sync(repository, settings, responses)
    responses.calls.clear()
    responses.history_id = "300"
    responses.messages["m2"] = message("m2")
    responses.history = {
        None: {
            "history": [{"messagesAdded": [{"message": {"id": "m1"}}]}],
            "nextPageToken": "next",
        },
        "next": {"history": [{"labelsAdded": [{"message": {"id": "m2"}}]}]},
    }
    result = sync(repository, settings, responses)
    assert result["saved"] == 1 and result["skipped"] == 1 and result["mode"] == "history"
    assert body_requests(responses) == ["m2"]
    assert not any(r.url.path.endswith("/messages") for r in responses.calls)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Mail)) == 2
        assert session.scalar(select(MailAccount.sync_cursor)) == "300"


def test_expired_history_rescans_only_since_original_start(database):
    engine, settings, repository, _ = connected(database, cursor="100")
    responses = GmailResponses({"old": message("old", START - timedelta(days=10)), "m1": message()})
    responses.expired_history = True
    assert sync(repository, settings, responses)["mode"] == "rescan"
    assert body_requests(responses) == ["m1"]
    with Session(engine) as session:
        assert session.scalar(select(MailAccount.sync_started_at)) == START


@pytest.mark.parametrize("rotate", [False, True])
def test_expired_token_refresh_is_encrypted_and_preserves_refresh_when_omitted(database, rotate):
    engine, settings, repository, account_id = connected(database, expired=True)
    responses = GmailResponses()
    responses.rotate_refresh = rotate
    result = sync(repository, settings, responses)
    assert result["token_refreshed"]
    payload = decrypted(engine, settings)
    assert payload["access_token"] == "new-access"
    assert payload["refresh_token"] == ("rotated-refresh" if rotate else "old-refresh")
    with Session(engine) as session:
        assert session.get(MailAccount, account_id).sync_started_at == START


def test_401_refreshes_once_but_invalid_grant_preserves_ciphertext(database):
    engine, settings, repository, _ = connected(database)
    responses = GmailResponses()
    responses.reject_old_access = True
    assert sync(repository, settings, responses)["token_refreshed"]
    assert sum(r.url.path == "/token" for r in responses.calls) == 1
    before = decrypted(engine, settings)
    responses = GmailResponses()
    responses.reject_old_access = True
    responses.fail_refresh = True
    # 자격 증명을 만료시켜 거부된 갱신 요청을 명시적으로 확인한다.
    with Session(engine) as session, session.begin():
        row = session.scalar(select(GoogleCredential))
        payload = dict(before)
        payload["expires_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        row.token_ciphertext = (
            Fernet(settings.encryption_key).encrypt(json.dumps(payload).encode()).decode()
        )
        ciphertext = row.token_ciphertext
    with pytest.raises(GoogleConnectionError):
        sync(repository, settings, responses)
    with Session(engine) as session:
        assert session.scalar(select(GoogleCredential.token_ciphertext)) == ciphertext


def test_failed_mail_batch_keeps_refreshed_token_but_rolls_back_mail_and_cursor(database):
    engine, settings, repository, _ = connected(database, expired=True)
    responses = GmailResponses({"m1": message(), "m2": message("m2")})
    responses.rotate_refresh = True
    responses.failed_ids = {"m2"}
    with pytest.raises(GoogleConnectionError):
        sync(repository, settings, responses)
    assert decrypted(engine, settings)["refresh_token"] == "rotated-refresh"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Mail)) == 0
        assert session.scalar(select(MailAccount.sync_cursor)) is None


def test_rotated_refresh_survives_failure_of_following_profile_request(database):
    engine, settings, repository, _ = connected(database, expired=True)
    responses = GmailResponses()
    responses.rotate_refresh = True
    responses.email = "unexpected@example.invalid"
    with pytest.raises(GoogleConnectionError):
        sync(repository, settings, responses)
    assert decrypted(engine, settings)["refresh_token"] == "rotated-refresh"
    with Session(engine) as session:
        assert session.scalar(select(MailAccount.sync_cursor)) is None
        assert session.scalar(select(func.count()).select_from(Mail)) == 0


def test_deleted_or_no_longer_inbox_messages_are_skipped_before_body_download(database):
    engine, settings, repository, _ = connected(database)
    responses = GmailResponses({"m1": message(), "archived": message("archived")})
    responses.messages["archived"]["labelIds"] = []
    responses.pages = {None: {"messages": [{"id": "deleted"}, {"id": "archived"}, {"id": "m1"}]}}
    result = sync(repository, settings, responses)
    assert result["saved"] == 1 and result["skipped"] == 2
    assert body_requests(responses) == ["m1"]


def test_concurrent_sync_serializes_cursor_and_keeps_one_mail(database):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    engine, settings, repository, _ = connected(database)
    paused, second_profile, release = threading.Event(), threading.Event(), threading.Event()

    class PausedResponses(GmailResponses):
        def __call__(self, request):
            if request.url.path.endswith("/profile") and paused.is_set():
                second_profile.set()
            if request.url.params.get("format") == "full" and not paused.is_set():
                paused.set()
                assert release.wait(10)
            return super().__call__(request)

    responses = PausedResponses()
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(sync, repository, settings, responses)
        second = None
        try:
            assert paused.wait(10)
            second = executor.submit(sync, repository, settings, responses)
            assert second_profile.wait(10)
            assert not second.done()
        finally:
            release.set()
        results = [first.result(timeout=10), second.result(timeout=10)]
    assert sorted(x["saved"] for x in results) == [0, 1]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Mail)) == 1
        assert session.scalar(select(MailAccount.sync_cursor)) == "200"


def test_wrong_key_or_wrong_profile_cannot_change_account_or_mail(database):
    engine, settings, repository, _ = connected(database)
    wrong = GoogleSettings(settings.client_id, settings.client_secret, EMAIL, Fernet.generate_key())
    responses = GmailResponses()
    with pytest.raises(GoogleConnectionError):
        sync(GmailSyncRepository(engine, wrong), wrong, responses)
    assert not responses.calls
    responses.email = "other@example.invalid"
    with pytest.raises(GoogleConnectionError):
        sync(repository, settings, responses)
    with Session(engine) as session:
        assert session.scalar(select(MailAccount.email)) == EMAIL
        assert session.scalar(select(MailAccount.sync_cursor)) is None
        assert session.scalar(select(func.count()).select_from(Mail)) == 0


def test_repeated_page_token_fails_without_advancing_cursor(database):
    engine, settings, repository, _ = connected(database)
    responses = GmailResponses()
    responses.pages = {
        None: {"messages": [{"id": "m1"}], "nextPageToken": "same"},
        "same": {"nextPageToken": "same"},
    }
    with pytest.raises(GoogleConnectionError):
        sync(repository, settings, responses)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Mail)) == 0
        assert session.scalar(select(MailAccount.sync_cursor)) is None


def test_html_plaintext_fallback_ignores_scripts_and_attachments():
    value = message(html=True)
    value["payload"]["parts"] = [
        {
            "filename": "hidden.txt",
            "mimeType": "text/plain",
            "body": {"data": base64.urlsafe_b64encode(b"attachment secret").decode()},
        }
    ]
    parsed = parse_message(value)
    assert parsed.body_text == "합성 & 본문"
    assert "hidden" not in parsed.body_text and "attachment" not in parsed.body_text


@pytest.mark.parametrize(
    "change",
    [
        {"internalDate": "bad"},
        {"id": "../unsafe"},
        {"payload": {"mimeType": "text/plain", "body": {"data": "!bad!"}}},
    ],
)
def test_malformed_message_has_only_safe_error(change):
    value = message()
    value.update(change)
    with pytest.raises(GoogleConnectionError) as error:
        parse_message(value)
    assert "합성" not in str(error.value) and "!bad!" not in str(error.value)


def test_cli_errors_never_echo_tokens_or_mail_content(monkeypatch, capsys):
    from app.cli import gmail_mail

    def failed():
        raise ValueError("synthetic-private-token-and-mail")

    monkeypatch.setattr(gmail_mail, "load_settings", failed)
    monkeypatch.setattr("sys.argv", ["gmail_mail", "sync"])
    with pytest.raises(SystemExit) as error:
        gmail_mail.main()
    assert "synthetic-private" not in str(error.value)
    assert not capsys.readouterr().out


def test_cli_shows_safe_reconnection_guidance(monkeypatch):
    from app.cli import gmail_mail

    def failed():
        raise GoogleConnectionError("기존 암호화 키·연결 토큰을 확인하세요")

    monkeypatch.setattr(gmail_mail, "load_settings", failed)
    monkeypatch.setattr("sys.argv", ["gmail_mail", "sync"])
    with pytest.raises(SystemExit, match="암호화 키"):
        gmail_mail.main()


def test_cli_sync_repeat_and_list_against_real_database(database, monkeypatch, capsys):
    from app.cli import gmail_mail

    engine, settings, _, _ = connected(database, expired=True)
    responses = GmailResponses()
    monkeypatch.setattr(gmail_mail, "load_settings", lambda: settings)
    monkeypatch.setattr(gmail_mail, "database_engine", lambda: engine)
    monkeypatch.setattr(
        gmail_mail,
        "GmailMailClient",
        lambda value: GmailMailClient(value, httpx.MockTransport(responses)),
    )
    outputs = []
    for action in ["sync", "sync", "list"]:
        monkeypatch.setattr("sys.argv", ["gmail_mail", action])
        gmail_mail.main()
        outputs.append(capsys.readouterr().out)
    first, second, listed = [json.loads(x) for x in outputs]
    assert first["saved"] == 1 and first["token_refreshed"]
    assert second["saved"] == 0 and listed["count"] == 1
    assert listed["mails"][0]["analysis_status"] == "pending"
    for output in outputs:
        for private in [
            "합성",
            "sender@example.invalid",
            "old-access",
            "old-refresh",
            "new-access",
        ]:
            assert private not in output
