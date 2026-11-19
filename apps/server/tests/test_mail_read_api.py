import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_gmail_mail_sync import connected
from test_postgresql_storage import database as database
from test_postgresql_storage import seed_account, store

from app.api.mail_read import MailAPIContext
from app.db.models import Mail, MailAccount
from app.db.repositories.google_connection import LOCAL_USER
from app.db.repositories.mail import MailRepository
from app.db.repositories.mail_query import MailQueryRepository
from app.mail_api_config import MailAPIConfigurationError, prepare_api_token, read_api_token
from app.main import create_app

TOKEN = "A" * 43


def client_for(repository=None, **kwargs):
    application = create_app()
    if repository is not None:
        application.state.mail_api = MailAPIContext(TOKEN, repository)
    return TestClient(
        application,
        base_url="http://127.0.0.1:8000",
        client=kwargs.pop("client", ("127.0.0.1", 12345)),
        **kwargs,
    )


def auth():
    return {"Authorization": "Bearer " + TOKEN}


class NoReads:
    def session(self):
        raise AssertionError("미인증 요청에서 저장소를 읽으면 안 됩니다")

    def list(self, **_):
        return self.session()

    def detail(self, _):
        return self.session()


@pytest.mark.parametrize(
    "authorization", [None, "Bearer wrong", "Basic bad", "Bearer " + "x" * 200]
)
def test_unauthenticated_requests_never_read_mail(authorization):
    headers = {"Authorization": authorization} if authorization else {}
    with client_for(NoReads()) as client:
        for path in ["/auth/session", "/mails", "/mails/private-id"]:
            response = client.get(path, headers=headers)
            assert response.status_code == 401
            assert response.headers["www-authenticate"] == "Bearer"
            assert response.json()["error"]["code"] == "unauthenticated"
            assert response.headers["cache-control"] == "no-store"
            assert TOKEN not in response.text


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://outside.invalid"},
        {"Origin": "null"},
        {"Host": "outside.invalid"},
        {"X-Forwarded-For": "127.0.0.1"},
    ],
)
def test_browser_origin_and_invalid_host_are_denied_even_with_token(headers):
    with client_for(NoReads()) as client:
        response = client.get("/mails", headers={**auth(), **headers})
        assert response.status_code == 403 and response.json()["error"]["code"] == "forbidden"


def test_remote_client_and_unconfigured_server_do_not_expose_data():
    with client_for(NoReads(), client=("192.0.2.1", 12345)) as remote:
        assert remote.get("/mails", headers=auth()).status_code == 403
    with client_for() as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/mails", headers=auth()).status_code == 503


def seeded(database):
    engine, settings, _, account_id = connected(database)
    with Session(engine) as session, session.begin():
        repository = MailRepository(session)
        account = session.get(MailAccount, account_id)
        start = account.sync_started_at
        for mail_id, offset in [("m-a", 0), ("m-b", 0), ("m-c", 1)]:
            repository.store_received(
                user_id=LOCAL_USER,
                account_id=account_id,
                mail_id=mail_id,
                source_message_id=mail_id,
                received_at=start + timedelta(seconds=offset),
                from_addr="sender@example.invalid",
                subject="합성 비공개 제목",
                body_text="합성 전용 본문 <script>실행 금지</script>",
                to=[{"addr": "to@example.invalid", "name": "수신자"}],
            )
        # 다른 사용자 및 같은 사용자의 다른 계정에 접근할 수 없어야 한다.
        store(
            seed_account(session, user_id="other-user", account_id="other-account"),
            user_id="other-user",
            account_id="other-account",
            mail_id="private-other",
        )
        repository.add_account(
            account_id="same-user-other-account",
            user_id=LOCAL_USER,
            source="gmail",
            email="another@example.invalid",
            sync_started_at=start,
        )
        repository.store_received(
            user_id=LOCAL_USER,
            account_id="same-user-other-account",
            mail_id="private-same-user",
            source_message_id="foreign",
            received_at=start,
            from_addr="foreign@example.invalid",
            subject="남의 제목",
            body_text="남의 본문",
        )
        # 기존 데이터에 과거·보낸 메일이 있더라도 이번 받은편지함 API에 보이지 않는다.
        session.add(
            Mail(
                mail_id="old",
                account_id=account_id,
                user_id=LOCAL_USER,
                source_message_id="old",
                direction="received",
                mailbox="inbox",
                received_at=start - timedelta(days=1),
                from_addr="old@example.invalid",
                subject="과거",
                body_text="과거",
            )
        )
        session.add(
            Mail(
                mail_id="sent",
                account_id=account_id,
                user_id=LOCAL_USER,
                source_message_id="sent",
                direction="sent",
                mailbox="sent",
                received_at=start,
                from_addr="sent@example.invalid",
                subject="보낸",
                body_text="보낸",
            )
        )
    return engine, settings, MailQueryRepository(engine, settings.expected_email)


def test_session_list_detail_and_ownership_boundaries(database):
    _, settings, repository = seeded(database)
    with client_for(repository) as client:
        session = client.get("/auth/session", headers=auth())
        assert session.status_code == 200 and session.json()["email"] == settings.expected_email
        response = client.get("/mails", headers=auth())
        assert response.status_code == 200
        assert [x["mail_id"] for x in response.json()["items"]] == ["m-c", "m-b", "m-a"]
        assert response.json()["next_cursor"] is None
        assert "body_text" not in response.json()["items"][0]
        detail = client.get("/mails/m-a", headers=auth())
        assert detail.status_code == 200
        assert detail.json()["body_text"] == "합성 전용 본문 <script>실행 금지</script>"
        assert "body_html" not in detail.json() and "token_ciphertext" not in detail.text
        assert detail.headers["referrer-policy"] == "no-referrer"
        for mail_id in ["private-other", "private-same-user", "old", "sent", "unknown"]:
            response = client.get("/mails/" + mail_id, headers=auth())
            assert response.status_code == 404
            assert "남의" not in response.text


def test_cursor_pagination_is_stable_for_equal_timestamps(database):
    _, _, repository = seeded(database)
    with client_for(repository) as client:
        cursor, identifiers = None, []
        for _ in range(3):
            params = {"limit": 1}
            if cursor:
                params["cursor"] = cursor
            response = client.get("/mails", headers=auth(), params=params)
            assert response.status_code == 200
            data = response.json()
            identifiers.extend(x["mail_id"] for x in data["items"])
            cursor = data["next_cursor"]
        assert identifiers == ["m-c", "m-b", "m-a"] and cursor is None
        assert client.get("/mails", headers=auth(), params={"limit": 0}).status_code == 422
        assert client.get("/mails", headers=auth(), params={"box": "sent"}).status_code == 422
        assert (
            client.get("/mails", headers=auth(), params={"user_id": "other-user"}).status_code
            == 422
        )
        assert client.get("/mails?limit=1&limit=2", headers=auth()).status_code == 422


@pytest.mark.parametrize(
    "cursor",
    [
        "!private-input!",
        "e30",
        base64.urlsafe_b64encode(json.dumps([1, "2026-01-01", "m-a"]).encode())
        .decode()
        .rstrip("="),
    ],
)
def test_invalid_cursor_does_not_echo_input(database, cursor):
    _, _, repository = seeded(database)
    with client_for(repository) as client:
        response = client.get("/mails", headers=auth(), params={"cursor": cursor})
        assert response.status_code == 422
        assert cursor not in response.text


def test_unexpected_private_exception_is_not_logged_or_returned(caplog):
    class Broken:
        def list(self, **_):
            raise RuntimeError("synthetic-private-body-and-token")

    with client_for(Broken(), raise_server_exceptions=False) as client:
        response = client.get("/mails", headers=auth())
        assert response.status_code == 500
        assert "synthetic-private" not in response.text + caplog.text
        assert response.headers["cache-control"] == "no-store"


def test_private_api_token_setup_never_changes_google_secrets(tmp_path):
    directory = tmp_path / ".local-secrets"
    directory.mkdir(mode=0o700)
    (directory / "token.key").write_bytes(b"synthetic-original-google-key")
    assert prepare_api_token(directory)
    token = read_api_token(directory)
    assert len(token) == 43
    assert (directory / "mail-api-token").stat().st_mode & 0o777 == 0o600
    assert not prepare_api_token(directory)
    assert read_api_token(directory) == token
    assert (directory / "token.key").read_bytes() == b"synthetic-original-google-key"
    (directory / "mail-api-token").write_text("invalid-private-value")
    with pytest.raises(MailAPIConfigurationError) as error:
        read_api_token(directory)
    assert "invalid-private-value" not in str(error.value)


def test_real_server_and_node_main_fetch_read_api(database, monkeypatch, capsys):
    if not shutil.which("node"):
        pytest.skip("Node가 없어 Electron main과 같은 fetch 경계 검사를 실행하지 않음")
    engine, settings, _ = seeded(database)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    env = {
        **os.environ,
        "MAIL_API_TEST_DB": engine.url.render_as_string(hide_password=False),
        "MAIL_API_TEST_EMAIL": settings.expected_email,
        "MAIL_API_TEST_PORT": str(port),
        "MAIL_API_TEST_TOKEN": TOKEN,
    }
    script = """
import os,sys
from types import SimpleNamespace
from sqlalchemy import create_engine
from app.cli import run_mail_api
run_mail_api.read_api_token=lambda:os.environ['MAIL_API_TEST_TOKEN']
run_mail_api.load_settings=lambda:SimpleNamespace(expected_email=os.environ['MAIL_API_TEST_EMAIL'])
run_mail_api.database_engine=lambda:create_engine(os.environ['MAIL_API_TEST_DB'],hide_parameters=True)
sys.argv=['run_mail_api','--port',os.environ['MAIL_API_TEST_PORT']]
run_mail_api.main()
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                response = httpx.get(
                    f"http://127.0.0.1:{port}/health", trust_env=False, timeout=0.3
                )
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            assert process.poll() is None and time.monotonic() < deadline
            time.sleep(0.05)
        node = """
(async()=>{
 const base='http://127.0.0.1:'+process.env.MAIL_API_TEST_PORT;
 const headers={Authorization:'Bearer '+process.env.MAIL_API_TEST_TOKEN};
 const session=await fetch(base+'/auth/session',{headers});
 const list=await fetch(base+'/mails?limit=1',{headers});
 const page=await list.json();
 const detail=await fetch(base+'/mails/'+page.items[0].mail_id,{headers});
 const body=await detail.json();
 const denied=await fetch(base+'/mails');
 console.log(JSON.stringify({session:session.status,list:list.status,detail:detail.status,
  denied:denied.status,bodyPresent:typeof body.body_text==='string',hasNext:!!page.next_cursor}));
})().catch(()=>process.exit(1));
"""
        result = subprocess.run(
            ["node", "-e", node], env=env, capture_output=True, text=True, timeout=10, check=True
        )
        assert json.loads(result.stdout) == {
            "session": 200,
            "list": 200,
            "detail": 200,
            "denied": 401,
            "bodyPresent": True,
            "hasNext": True,
        }
        from app.cli import check_mail_api

        monkeypatch.setattr(check_mail_api, "read_api_token", lambda: TOKEN)
        monkeypatch.setattr("sys.argv", ["check_mail_api", "--port", str(port)])
        check_mail_api.main()
        output = capsys.readouterr().out
        assert json.loads(output) == {
            "status": "ok",
            "session": "ok",
            "listed": 3,
            "detail": "ok",
            "has_next_page": False,
        }
        assert (
            TOKEN not in output and "합성" not in output and settings.expected_email not in output
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
