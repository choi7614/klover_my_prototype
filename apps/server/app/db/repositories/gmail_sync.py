"""기존 계정·키를 사용하는 자격 증명 갱신과 메일 배치의 별도 트랜잭션."""

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GoogleCredential, Mail, MailAccount
from app.db.repositories.google_connection import LOCAL_USER
from app.db.repositories.mail import MailRepository
from app.google_config import GMAIL_SCOPE, GoogleConnectionError


@dataclass(repr=False)
class Credentials:
    tokens: dict = field(repr=False)


class SyncBatch:
    def __init__(self, session, account):
        self.session, self.account = session, account

    @property
    def start(self):
        return self.account.sync_started_at

    @property
    def cursor(self):
        return self.account.sync_cursor

    def contains(self, source_id: str) -> bool:
        return (
            self.session.scalar(
                select(Mail.mail_id).where(
                    Mail.account_id == self.account.account_id,
                    Mail.user_id == self.account.user_id,
                    Mail.source_message_id == source_id,
                )
            )
            is not None
        )

    def store(self, message) -> None:
        MailRepository(self.session).store_received(
            user_id=self.account.user_id,
            account_id=self.account.account_id,
            mail_id=str(uuid4()),
            source_message_id=message.source_id,
            received_at=message.received_at,
            from_addr=message.from_addr,
            from_name=message.from_name,
            to=message.to,
            cc=message.cc,
            subject=message.subject,
            body_text=message.body_text,
            thread_id=message.thread_id,
            is_read=message.is_read,
        )

    def advance(self, cursor: str) -> None:
        self.account.sync_cursor = cursor


class GmailSyncRepository:
    def __init__(self, engine, settings):
        self.engine = engine
        self.email = settings.expected_email
        self._cipher = Fernet(settings.encryption_key)

    def _account(self, session, *, lock=False):
        query = select(MailAccount).where(
            MailAccount.user_id == LOCAL_USER,
            MailAccount.source == "gmail",
            MailAccount.email == self.email,
        )
        if lock:
            query = query.with_for_update()
        account = session.scalar(query)
        if account is None:
            raise GoogleConnectionError("먼저 테스트 Gmail 계정을 연결하세요")
        return account

    @contextmanager
    def credentials(self):
        with Session(self.engine) as session, session.begin():
            account = self._account(session)
            row = session.scalar(
                select(GoogleCredential)
                .where(
                    GoogleCredential.account_id == account.account_id,
                )
                .with_for_update()
            )
            if row is None:
                raise GoogleConnectionError("연결 토큰이 없습니다. Google에 다시 연결하세요")
            try:
                tokens = json.loads(self._cipher.decrypt(row.token_ciphertext.encode()))
                if not isinstance(tokens, dict) or tokens.get("scope") != GMAIL_SCOPE:
                    raise ValueError
                for key in ["access_token", "refresh_token"]:
                    if not isinstance(tokens[key], str) or not 1 <= len(tokens[key]) <= 16384:
                        raise ValueError
                expires = datetime.fromisoformat(tokens["expires_at"])
                if expires.tzinfo is None or expires.utcoffset() is None:
                    raise ValueError
            except (InvalidToken, ValueError, KeyError, TypeError):
                raise GoogleConnectionError("기존 암호화 키·연결 토큰을 확인하세요") from None
            original = dict(tokens)
            value = Credentials(tokens)
            yield value
            if value.tokens != original:
                row.token_ciphertext = self._cipher.encrypt(
                    json.dumps(value.tokens).encode()
                ).decode()
                row.updated_at = datetime.now(UTC)

    @contextmanager
    def batch(self):
        # 같은 계정의 동시 수신은 직렬화해 커서와 메일을 함께 저장한다.
        with Session(self.engine) as session, session.begin():
            yield SyncBatch(session, self._account(session, lock=True))

    def list_received(self, limit=50):
        with Session(self.engine) as session:
            account = self._account(session)
            rows = MailRepository(session).list_received(
                user_id=account.user_id,
                account_id=account.account_id,
                limit=limit,
            )
            # 터미널·검사 로그에 제목·본문·주소를 출력하지 않는다.
            return [
                {
                    "mail_id": row.mail_id,
                    "received_at": row.received_at.isoformat(),
                    "analysis_status": row.analysis_status,
                }
                for row in rows
            ]
