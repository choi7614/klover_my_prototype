import hashlib
import json
import time
from base64 import urlsafe_b64encode
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.api.google_connection import COOKIE, create_google_app
from app.cli.configure_google import configure
from app.connectors.google_oauth import GoogleOAuthClient, LoginAttempts
from app.google_config import (
    GMAIL_SCOPE,
    REDIRECT_URI,
    GoogleConnectionError,
    GoogleSettings,
    load_settings,
)

EMAIL = "test-user@example.invalid"
ACCESS = "synthetic-access-token-private"
REFRESH = "synthetic-refresh-token-private"


@pytest.fixture
def settings():
    return GoogleSettings("synthetic-client", "synthetic-secret", EMAIL, Fernet.generate_key())


def transport(*, status=200, email=EMAIL, token_overrides=None):
    def handle(request):
        if str(request.url) == "https://oauth2.googleapis.com/token":
            values = parse_qs(request.content.decode())
            assert values["redirect_uri"] == [REDIRECT_URI]
            assert values["grant_type"] == ["authorization_code"]
            assert len(values["code_verifier"][0]) >= 43
            return httpx.Response(
                status,
                json={
                    "access_token": ACCESS,
                    "refresh_token": REFRESH,
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": GMAIL_SCOPE,
                    **(token_overrides or {}),
                },
            )
        assert str(request.url) == "https://gmail.googleapis.com/gmail/v1/users/me/profile"
        assert request.headers["authorization"] == "Bearer " + ACCESS
        return httpx.Response(200, json={"emailAddress": email})

    return httpx.MockTransport(handle)


class SavedConnection:
    def __init__(self):
        self.saved = []

    def save(self, email, tokens):
        self.saved.append((email, tokens))


def client_for(settings, repository, mock=None):
    app = create_google_app(settings, GoogleOAuthClient(settings, mock or transport()), repository)
    return TestClient(app, base_url="http://localhost:8000", client=("127.0.0.1", 12345))


def begin(client):
    page = client.get("/auth/google")
    assert page.status_code == 200
    browser = client.cookies[COOKIE]
    assert "HttpOnly" in page.headers["set-cookie"]
    assert "SameSite=lax" in page.headers["set-cookie"]
    assert page.headers["referrer-policy"] == "same-origin"
    assert (
        "form-action 'self' https://accounts.google.com;" in page.headers["content-security-policy"]
    )
    response = client.post(
        "/auth/google",
        data={"csrf": browser},
        headers={"origin": "http://localhost:8000"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return parse_qs(urlparse(response.headers["location"]).query)


def test_browser_flow_exchanges_code_confirms_email_and_never_returns_tokens(settings):
    repository = SavedConnection()
    with client_for(settings, repository) as client:
        values = begin(client)
        assert values["scope"] == [GMAIL_SCOPE]
        assert values["access_type"] == ["offline"]
        assert values["redirect_uri"] == [REDIRECT_URI]
        assert values["code_challenge_method"] == ["S256"]
        result = client.get(
            "/auth/google/callback", params={"state": values["state"][0], "code": "synthetic-code"}
        )
        assert result.status_code == 200
        assert EMAIL in result.text
        assert ACCESS not in result.text and REFRESH not in result.text
        assert "no-store" in result.headers["cache-control"]
        assert result.headers["referrer-policy"] == "no-referrer"
        assert "form-action 'self';" in result.headers["content-security-policy"]
        assert COOKIE not in client.cookies
        assert len(repository.saved) == 1
        replay = client.get(
            "/auth/google/callback", params={"state": values["state"][0], "code": "synthetic-code"}
        )
        assert replay.status_code == 400
        assert len(repository.saved) == 1


@pytest.mark.parametrize(
    "email,status,override",
    [
        ("other@example.invalid", 200, {}),
        (EMAIL, 400, {}),
        (EMAIL, 200, {"scope": ""}),
        (EMAIL, 200, {"scope": GMAIL_SCOPE + " https://www.googleapis.com/auth/calendar"}),
        (EMAIL, 200, {"expires_in": "bad"}),
        (EMAIL, 200, {"access_token": ""}),
    ],
)
def test_google_rejection_does_not_save_or_echo_private_response(settings, email, status, override):
    repository = SavedConnection()
    with client_for(
        settings, repository, transport(status=status, email=email, token_overrides=override)
    ) as client:
        values = begin(client)
        result = client.get(
            "/auth/google/callback", params={"state": values["state"][0], "code": "synthetic-code"}
        )
        assert result.status_code == 400
        assert not repository.saved
        assert ACCESS not in result.text and REFRESH not in result.text
        assert email not in result.text


def test_csrf_origin_and_nonlocal_requests_are_rejected(settings):
    repository = SavedConnection()
    with client_for(settings, repository) as client:
        client.get("/auth/google")
        for headers, data in [
            ({}, {"csrf": client.cookies[COOKIE]}),
            ({"origin": "null"}, {"csrf": client.cookies[COOKIE]}),
            ({"origin": "https://outside.invalid"}, {"csrf": client.cookies[COOKIE]}),
            ({"origin": "http://localhost:8000"}, {"csrf": "bad"}),
            ({"origin": "http://localhost:8000"}, {"csrf": "한글"}),
        ]:
            assert client.post("/auth/google", headers=headers, data=data).status_code in (400, 403)
        assert client.get("/auth/google", headers={"host": "outside.invalid"}).status_code == 403
        assert client.get("/auth/google", headers={"x-forwarded-for": "8.8.8.8"}).status_code == 403
        assert not repository.saved
    app = create_google_app(settings, GoogleOAuthClient(settings), repository)
    with TestClient(app, base_url="http://localhost:8000", client=("192.0.2.1", 100)) as remote:
        assert remote.get("/auth/google").status_code == 403


def test_missing_wrong_cookie_and_cancelled_flow_never_save(settings):
    repository = SavedConnection()
    with client_for(settings, repository) as client:
        values = begin(client)
        client.cookies.clear()
        assert (
            client.get(
                "/auth/google/callback", params={"state": values["state"][0], "code": "synthetic"}
            ).status_code
            == 400
        )
        values = begin(client)
        assert (
            client.get(
                "/auth/google/callback",
                params={"state": values["state"][0], "error": "access_denied"},
            ).status_code
            == 400
        )
        assert not repository.saved


def test_attempt_expiry_browser_binding_and_pkce(settings, monkeypatch):
    attempts = LoginAttempts()
    state, verifier = attempts.begin("browser-a")
    with pytest.raises(GoogleConnectionError):
        attempts.consume(state, "browser-b")
    assert attempts.consume(state, "browser-a") == verifier
    with pytest.raises(GoogleConnectionError):
        attempts.consume(state, "browser-a")
    state, _ = attempts.begin("browser-a")
    now = time.monotonic()
    monkeypatch.setattr("app.connectors.google_oauth.time.monotonic", lambda: now + 601)
    with pytest.raises(GoogleConnectionError):
        attempts.consume(state, "browser-a")


def test_pkce_challenge_matches_the_verifier_used_for_token_exchange(settings):
    captured = {}
    original = transport()

    def handle(request):
        if request.method == "POST":
            captured.update(parse_qs(request.content.decode()))
        return original.handle_request(request)

    with client_for(settings, SavedConnection(), httpx.MockTransport(handle)) as client:
        values = begin(client)
        result = client.get(
            "/auth/google/callback", params={"state": values["state"][0], "code": "synthetic"}
        )
        assert result.status_code == 200
        challenge = (
            urlsafe_b64encode(hashlib.sha256(captured["code_verifier"][0].encode()).digest())
            .decode()
            .rstrip("=")
        )
        assert values["code_challenge"] == [challenge]


def test_local_settings_copy_is_private_and_existing_key_is_preserved(tmp_path, settings):
    source = tmp_path / "download.json"
    source.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": settings.client_id,
                    "client_secret": settings.client_secret,
                    "redirect_uris": [REDIRECT_URI],
                    "token_uri": "https://outside.invalid",
                }
            }
        )
    )
    directory = tmp_path / ".local-secrets"
    configure(source, EMAIL, directory)
    loaded = load_settings(directory)
    assert loaded.expected_email == EMAIL
    assert settings.client_secret not in repr(loaded)
    original_key = (directory / "token.key").read_bytes()
    for file in directory.iterdir():
        assert file.stat().st_mode & 0o777 == 0o600
    assert directory.stat().st_mode & 0o777 == 0o700
    with pytest.raises(GoogleConnectionError):
        configure(source, EMAIL, directory)
    assert (directory / "token.key").read_bytes() == original_key
    assert "token_uri" not in (directory / "google-client.json").read_text()


@pytest.mark.parametrize("payload", [{"installed": {}}, {"web": {"redirect_uris": []}}])
def test_invalid_google_json_creates_no_secret_directory(tmp_path, payload):
    source = tmp_path / "download.json"
    source.write_text(json.dumps(payload))
    destination = tmp_path / ".local-secrets"
    with pytest.raises(GoogleConnectionError):
        configure(source, EMAIL, destination)
    assert not destination.exists()


def test_database_failure_never_exposes_token_or_exception(settings):
    from sqlalchemy.exc import SQLAlchemyError

    class FailedRepository:
        def save(self, email, tokens):
            raise SQLAlchemyError("synthetic-private-database-detail")

    with client_for(settings, FailedRepository()) as client:
        values = begin(client)
        result = client.get(
            "/auth/google/callback",
            params={"state": values["state"][0], "code": "synthetic-private-code"},
        )
        assert result.status_code == 503
        for secret in [
            ACCESS,
            REFRESH,
            "synthetic-private-database-detail",
            "synthetic-private-code",
        ]:
            assert secret not in result.text


def test_connection_launcher_disables_access_logging_and_proxy_trust(settings, monkeypatch, capsys):
    from app.cli import run_google_connection

    class FakeEngine:
        disposed = False

        def dispose(self):
            self.disposed = True

    engine = FakeEngine()
    captured = {}
    monkeypatch.setattr(run_google_connection, "load_settings", lambda: settings)
    monkeypatch.setattr(run_google_connection, "database_engine", lambda: engine)
    monkeypatch.setattr(
        run_google_connection.uvicorn, "run", lambda app, **options: captured.update(options)
    )
    run_google_connection.main()
    assert captured["access_log"] is False and captured["proxy_headers"] is False
    assert captured["host"] == "127.0.0.1" and captured["workers"] == 1
    assert engine.disposed
    output = capsys.readouterr().out
    assert settings.client_secret not in output and settings.encryption_key.decode() not in output
