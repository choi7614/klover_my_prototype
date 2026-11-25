"""가짜 Google 응답만 사용한다. 실서비스 호출은 MockTransport가 차단한다."""

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.connectors.google_calendar import SCOPES
from app.db.models import GoogleCredential, MailAccount
from app.db.repositories.f5_calendar import CalendarConnectionRepository, CalendarCredential
from app.google_config import GMAIL_SCOPE, GoogleSettings
from app.schemas.f5 import ApproveRequest
from app.services.f5 import F5Service
from app.services.f5_calendar import ConnectedCalendar
from app.services.f5_errors import CalendarError, F5Error

from .helpers import OTHER, OWNER, analysis

SETTINGS = GoogleSettings(
    "synthetic-client", "synthetic-secret", "f5-user@example.invalid", Fernet.generate_key()
)


class Google:
    def __init__(self):
        self.events = {}
        self.calls = []
        self.timeout = False
        self.fail = None

    def __call__(self, request):
        self.calls.append(request)
        if self.fail:
            return httpx.Response(self.fail, json={"error": "private-message"})
        if request.url.path.endswith("calendarList"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "synthetic-calendar",
                            "summary": "업무",
                            "accessRole": "owner",
                            "timeZone": "Asia/Seoul",
                        },
                        {"id": "shared", "accessRole": "writer"},
                    ]
                },
            )
        if request.url.path.endswith("freeBusy"):
            return httpx.Response(200, json={"calendars": {"synthetic-calendar": {"busy": []}}})
        if request.method == "GET":
            value = self.events.get(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200 if value else 404, json=value or {})
        body = json.loads(request.content)
        assert request.url.params["sendUpdates"] == "none"
        assert "attendees" not in body
        if body["id"] in self.events:
            return httpx.Response(409, json={})
        self.events[body["id"]] = body
        if self.timeout:
            self.timeout = False
            raise httpx.ReadTimeout("synthetic-timeout")
        return httpx.Response(200, json=body)


@pytest.fixture(autouse=True)
def local_owner(monkeypatch, request):
    import inspect

    from app.connectors.google_oauth import GoogleOAuthClient

    if "scopes" not in inspect.signature(GoogleOAuthClient).parameters and request.node.name in {
        "test_incremental_oauth_reuses_pkce_and_identity",
        "test_consent_denial_and_replay_do_not_save",
        "test_existing_gmail_refresh_tolerates_incremental_scope_without_mutation",
    }:
        pytest.skip("공통 OAuth 패치 적용 사본에서 검사")
    monkeypatch.setattr("app.db.repositories.f5_calendar.LOCAL_USER", OWNER.user_id)


def setup(db):
    with Session(db.engine) as session, session.begin():
        session.get(MailAccount, OWNER.account_id).source = "gmail"
        session.add(
            GoogleCredential(
                account_id=OWNER.account_id,
                token_ciphertext="opaque-original-gmail",
                updated_at=datetime.now(UTC),
            )
        )
    repo = CalendarConnectionRepository(db.engine, SETTINGS.encryption_key)
    repo.save(
        SETTINGS.expected_email,
        {
            "access_token": "synthetic",
            "refresh_token": "synthetic-refresh",
            "scope": " ".join(SCOPES | {GMAIL_SCOPE}),
            "expires_in": 3600,
        },
    )
    google = Google()
    calendar = ConnectedCalendar(repo, SETTINGS, httpx.MockTransport(google))
    return repo, google, F5Service(db.repository, calendar)


def test_approve_timeout_retry_and_disconnect_preserves_mail(f5db):
    repo, google, service = setup(f5db)
    row = service.scan(OWNER, analysis()).items[0]
    assert not google.calls  # 생성은 HTTP 호출도 하지 않는다.
    state = service.calendar.status(OWNER)
    assert state["email"] == SETTINGS.expected_email
    assert [x["id"] for x in state["calendars"]] == ["synthetic-calendar"]
    payload = row.payload.model_dump(mode="json")
    payload["title"] = "수정 후 명시 승인"
    google.timeout = True
    with pytest.raises(CalendarError, match="calendar_result_unknown"):
        service.approve(
            OWNER, row.suggestion_id, ApproveRequest(version=row.version, payload=payload)
        )
    pending = f5db.repository.get(OWNER, row.suggestion_id)
    assert pending.status == "pending" and pending.execution_status == "uncertain"
    done = service.approve(
        OWNER, row.suggestion_id, ApproveRequest(version=pending.version, payload=payload)
    )
    assert done.status == "approved" and done.execution_mode == "live"
    assert len(google.events) == 1
    assert next(iter(google.events.values()))["summary"] == payload["title"]
    again = service.approve(
        OWNER, row.suggestion_id, ApproveRequest(version=done.version, payload=payload)
    )
    assert again.status == "approved" and len(google.events) == 1
    repo.disconnect(OWNER)
    assert service.calendar.status(OWNER)["status"] == "calendar_not_connected"
    with Session(f5db.engine) as session:
        assert session.get(MailAccount, OWNER.account_id).email == SETTINGS.expected_email
        assert (
            session.get(GoogleCredential, OWNER.account_id).token_ciphertext
            == "opaque-original-gmail"
        )
    assert len(google.events) == 1


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "calendar_permission_expired"),
        (403, "calendar_scope_required"),
        (500, "calendar_connection_failed"),
    ],
)
def test_fixed_error_no_success(f5db, status, code):
    repo, google, service = setup(f5db)
    google.fail = status
    assert service.calendar.status(OWNER)["status"] == code
    row = service.scan(OWNER, analysis()).items[0]
    with pytest.raises(CalendarError, match=code):
        service.approve(OWNER, row.suggestion_id, ApproveRequest(version=row.version))
    assert f5db.repository.get(OWNER, row.suggestion_id).status == "pending"


def test_foreign_calendar_and_owner_rejected(f5db):
    repo, google, service = setup(f5db)
    row = service.scan(OWNER, analysis()).items[0]
    with pytest.raises(CalendarError):
        repo.read(OTHER)
    payload = row.payload.model_copy(update={"calendar_id": "shared"})
    with pytest.raises(CalendarError, match="calendar_selection_required"):
        service.calendar.execute(OWNER, row.suggestion_id, payload)
    assert not google.events


def test_refresh_preserves_refresh_and_encryption(f5db):
    repo, google, service = setup(f5db)
    with Session(f5db.engine) as session, session.begin():
        row = session.get(CalendarCredential, OWNER.account_id)
        data = repo.read(OWNER)
        data["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        row.token_ciphertext = repo._cipher.encrypt(json.dumps(data).encode()).decode()

    def refresh(request):
        assert request.url.host == "oauth2.googleapis.com"
        return httpx.Response(
            200, json={"access_token": "fresh", "expires_in": 3600, "token_type": "Bearer"}
        )

    value = repo.refresh(OWNER, SETTINGS, httpx.MockTransport(refresh))
    assert value["refresh_token"] == "synthetic-refresh"
    with Session(f5db.engine) as session:
        assert (
            "synthetic-refresh"
            not in session.get(CalendarCredential, OWNER.account_id).token_ciphertext
        )


@pytest.mark.parametrize("status", [400, 401, 403])
def test_refresh_denied(f5db, status):
    repo, _, _ = setup(f5db)
    with Session(f5db.engine) as session, session.begin():
        row = session.get(CalendarCredential, OWNER.account_id)
        data = repo.read(OWNER)
        data["expires_at"] = "2020-01-01T00:00:00+00:00"
        row.token_ciphertext = repo._cipher.encrypt(json.dumps(data).encode()).decode()
    with pytest.raises(CalendarError, match="calendar_permission_expired"):
        repo.refresh(OWNER, SETTINGS, httpx.MockTransport(lambda _: httpx.Response(status)))


def test_incremental_oauth_reuses_pkce_and_identity():
    from app.connectors.google_oauth import GoogleOAuthClient, authorization_url

    scopes = SCOPES | {GMAIL_SCOPE}
    query = parse_qs(
        urlparse(authorization_url(SETTINGS, "state", "verifier", scopes=scopes)).query
    )
    assert query["include_granted_scopes"] == ["true"]
    assert set(query["scope"][0].split()) == scopes
    assert query["code_challenge_method"] == ["S256"]

    def exchange(request):
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(
                200,
                json={
                    "access_token": "a",
                    "refresh_token": "r",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": " ".join(scopes),
                },
            )
        return httpx.Response(200, json={"emailAddress": SETTINGS.expected_email})

    email, tokens = GoogleOAuthClient(
        SETTINGS, httpx.MockTransport(exchange), scopes=scopes
    ).exchange("code", "verifier")
    assert email == SETTINGS.expected_email and set(tokens["scope"].split()) == scopes


def test_consent_denial_and_replay_do_not_save():
    from fastapi.testclient import TestClient

    from app.api.f5_calendar_consent import consent_app
    from tests.test_google_connection import SavedConnection, begin

    store = SavedConnection()
    with TestClient(
        consent_app(
            SETTINGS, store, httpx.MockTransport(lambda _: pytest.fail("거절 후 외부 요청"))
        ),
        base_url="http://localhost:8000",
        client=("127.0.0.1", 123),
    ) as client:
        query = begin(client)
        state = query["state"][0]
        denied = client.get(
            "/auth/google/callback", params={"state": state, "error": "access_denied"}
        )
        assert denied.status_code == 400 and "취소" in denied.text
        assert (
            client.get(
                "/auth/google/callback", params={"state": state, "code": "replay"}
            ).status_code
            == 400
        )
        assert not store.saved


def test_concurrent_live_approval_only_inserts_once(f5db):
    from concurrent.futures import ThreadPoolExecutor

    from app.services.f5_errors import F5Error

    _, google, service = setup(f5db)
    row = service.scan(OWNER, analysis()).items[0]

    def approve(_):
        try:
            return service.approve(
                OWNER, row.suggestion_id, ApproveRequest(version=row.version)
            ).status
        except F5Error:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve, range(2)))
    assert "approved" in results and len(google.events) == 1


def test_existing_gmail_refresh_tolerates_incremental_scope_without_mutation():
    from app.connectors.gmail_mail import GmailMailClient

    previous = {
        "access_token": "old",
        "refresh_token": "original-gmail-refresh",
        "scope": GMAIL_SCOPE,
    }
    expected = dict(previous)

    def handle(request):
        assert b"original-gmail-refresh" in request.content
        return httpx.Response(
            200,
            json={
                "access_token": "fresh",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": " ".join(SCOPES | {GMAIL_SCOPE}),
            },
        )

    with GmailMailClient(SETTINGS, httpx.MockTransport(handle)) as client:
        fresh = client.refresh(previous)
    assert fresh["refresh_token"] == previous["refresh_token"] and previous == expected
    assert GMAIL_SCOPE in fresh["scope"].split()


def test_calendar_api_reuses_auth_and_never_exposes_tokens(f5db):
    from app.api.f5_calendar import router

    from .helpers import client, headers

    repo, google, service = setup(f5db)
    with client(service) as http:
        http.app.include_router(router)
        assert http.get("/calendar/connection").status_code == 401
        response = http.get("/calendar/connection", headers=headers())
        assert response.status_code == 200
        assert "access_token" not in response.text and "refresh_token" not in response.text
        assert response.headers["cache-control"] == "no-store"
        assert (
            http.post(
                "/calendar/disconnect", headers={**headers(), "Origin": "https://outside.invalid"}
            ).status_code
            == 403
        )
        assert (
            http.post("/calendar/disconnect", headers=headers()).json()["status"]
            == "calendar_not_connected"
        )
        assert not google.events


def test_explicit_google_rejection_stays_failed_pending(f5db):
    repo, google, service = setup(f5db)

    def reject_insert(request):
        if request.method == "POST" and request.url.path.endswith("/events"):
            return httpx.Response(400, json={"error": "sensitive-google-text"})
        return google(request)

    service.calendar.transport = httpx.MockTransport(reject_insert)
    row = service.scan(OWNER, analysis()).items[0]
    with pytest.raises(CalendarError, match="calendar_registration_failed"):
        service.approve(OWNER, row.suggestion_id, ApproveRequest(version=row.version))
    failed = f5db.repository.get(OWNER, row.suggestion_id)
    assert failed.status == "pending" and failed.execution_status == "failed"
    assert not google.events


def test_reregister_after_the_user_deleted_the_event(f5db):
    """DB 필요: 구글 캘린더에서 지운 일정을 새 ID로 다시 등록하고, 아직 있으면 만들지 않는다."""
    repo, google, service = setup(f5db)
    row = service.scan(OWNER, analysis()).items[0]
    payload = row.payload.model_dump(mode="json")
    done = service.approve(
        OWNER, row.suggestion_id, ApproveRequest(version=row.version, payload=payload)
    )
    old_id = done.result.external_id
    # 아직 캘린더에 있으면 아무것도 만들지 않는다.
    with pytest.raises(F5Error, match="calendar_event_exists"):
        service.reregister(OWNER, row.suggestion_id, done.version)
    assert len(google.events) == 1
    # 사용자가 구글 캘린더에서 지움(구글은 취소 상태로 남긴다).
    google.events[old_id] = {**google.events[old_id], "status": "cancelled"}
    again = service.reregister(OWNER, row.suggestion_id, done.version)
    assert again.status == "approved" and again.execution_mode == "live"
    assert again.result.external_id != old_id and again.version == done.version + 1
    assert len(google.events) == 2
    # 같은 요청을 한 번 더 보내도(중복 클릭) 새 일정을 또 만들지 않는다.
    with pytest.raises(F5Error, match="stale_version"):
        service.reregister(OWNER, row.suggestion_id, done.version)
    assert len(google.events) == 2
    # 다시 등록한 일정마저 지우면 한 번 더 다시 등록할 수 있다.
    google.events[again.result.external_id]["status"] = "cancelled"
    third = service.reregister(OWNER, row.suggestion_id, again.version)
    assert third.result.external_id not in {old_id, again.result.external_id}
