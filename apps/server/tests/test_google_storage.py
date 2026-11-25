import json
from datetime import UTC, datetime

import pytest
from alembic import command
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database
from test_postgresql_storage import seed_account

from app.db.models import GoogleCredential, Mail, MailAccount, User
from app.db.repositories.google_connection import GoogleConnectionRepository
from app.google_config import GMAIL_SCOPE, GoogleConnectionError

EMAIL = "test-user@example.invalid"


def tokens(**overrides):
    return {
        "access_token": "synthetic-private-access",
        "refresh_token": "synthetic-private-refresh",
        "expires_in": 3600,
        "scope": GMAIL_SCOPE,
        **overrides,
    }


def test_encrypted_tokens_persist_and_reconnect_preserves_account_start(database):
    engine, _ = database
    key = Fernet.generate_key()
    repository = GoogleConnectionRepository(engine, key)
    repository.save(EMAIL, tokens())
    with Session(engine) as session:
        account = session.scalar(select(MailAccount))
        account_id, start = account.account_id, account.sync_started_at
        ciphertext = session.scalar(select(GoogleCredential.token_ciphertext))
        assert "synthetic-private" not in ciphertext
        assert (
            json.loads(Fernet(key).decrypt(ciphertext.encode()))["refresh_token"]
            == tokens()["refresh_token"]
        )
        with pytest.raises(InvalidToken):
            Fernet(Fernet.generate_key()).decrypt(ciphertext.encode())
    engine.dispose()
    GoogleConnectionRepository(engine, key).save(
        EMAIL, tokens(access_token="synthetic-new-access", refresh_token=None)
    )
    with Session(engine) as session:
        account = session.scalar(select(MailAccount))
        assert account.account_id == account_id and account.sync_started_at == start
        assert session.scalar(select(func.count()).select_from(MailAccount)) == 1
        ciphertext = session.scalar(select(GoogleCredential.token_ciphertext))
        payload = json.loads(Fernet(key).decrypt(ciphertext.encode()))
        assert payload["access_token"] == "synthetic-new-access"
        assert payload["refresh_token"] == tokens()["refresh_token"]
        assert datetime.fromisoformat(payload["expires_at"]) > datetime.now(UTC)


def test_missing_offline_token_rolls_back_and_existing_account_is_not_replaced(database):
    engine, _ = database
    repository = GoogleConnectionRepository(engine, Fernet.generate_key())
    with pytest.raises(GoogleConnectionError):
        repository.save(EMAIL, tokens(refresh_token=None))
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
    repository.save(EMAIL, tokens())
    with pytest.raises(GoogleConnectionError):
        repository.save("other@example.invalid", tokens())
    with Session(engine) as session:
        assert session.scalar(select(MailAccount.email)) == EMAIL
        assert session.scalar(select(func.count()).select_from(GoogleCredential)) == 1


def test_wrong_encryption_key_does_not_replace_existing_credentials(database):
    engine, _ = database
    GoogleConnectionRepository(engine, Fernet.generate_key()).save(EMAIL, tokens())
    with Session(engine) as session:
        before = session.scalar(select(GoogleCredential.token_ciphertext))
    with pytest.raises(GoogleConnectionError):
        GoogleConnectionRepository(engine, Fernet.generate_key()).save(
            EMAIL, tokens(refresh_token=None)
        )
    with Session(engine) as session:
        assert session.scalar(select(GoogleCredential.token_ciphertext)) == before


def test_new_migration_preserves_existing_mail_data(database):
    engine, config = database
    command.downgrade(config, "0001")
    with Session(engine) as session, session.begin():
        # 0001 구조에 자료를 넣은 뒤 최신 이력으로 올려 보존을 검사한다.
        from sqlalchemy import MetaData, Table

        seed_account(session)
        old_mail = Table("mails", MetaData(), autoload_with=session.connection())
        session.execute(
            old_mail.insert().values(
                mail_id="old",
                user_id="user-a",
                account_id="account-a",
                source_message_id="old",
                received_at=datetime(2026, 11, 18, tzinfo=UTC),
                direction="received",
                from_addr="synthetic@example.invalid",
                subject="합성",
                body_text="합성",
                to=[],
            )
        )
    command.upgrade(config, "head")
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Mail)) == 1
        assert session.scalar(select(func.count()).select_from(GoogleCredential)) == 0


def test_browser_to_real_database_uses_encryption(database):
    from test_google_connection import begin, client_for

    from app.google_config import GoogleSettings

    engine, _ = database
    settings = GoogleSettings("synthetic-client", "synthetic-secret", EMAIL, Fernet.generate_key())
    repository = GoogleConnectionRepository(engine, settings.encryption_key)
    with client_for(settings, repository) as client:
        values = begin(client)
        result = client.get(
            "/auth/google/callback", params={"state": values["state"][0], "code": "synthetic-code"}
        )
        assert result.status_code == 200
    with Session(engine) as session:
        ciphertext = session.scalar(select(GoogleCredential.token_ciphertext))
        assert "synthetic-access-token" not in ciphertext
        assert "synthetic-refresh-token" not in ciphertext
        payload = json.loads(Fernet(settings.encryption_key).decrypt(ciphertext.encode()))
        assert payload["refresh_token"] == "synthetic-refresh-token-private"
