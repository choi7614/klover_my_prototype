"""로컬 운영자 한 명의 연결만 저장한다. 외부 앱 로그인·다중 사용자 인증은 후속 범위다."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import GoogleCredential, MailAccount, User
from app.google_config import GoogleConnectionError

LOCAL_USER = "local-development"


class GoogleConnectionRepository:
    def __init__(self, engine, key: bytes):
        self.engine = engine
        self._cipher = Fernet(key)

    def save(self, email: str, tokens: dict) -> None:
        with Session(self.engine) as session, session.begin():
            session.execute(insert(User).values(user_id=LOCAL_USER).on_conflict_do_nothing())
            session.scalar(select(User).where(User.user_id == LOCAL_USER).with_for_update())
            account = session.scalar(
                select(MailAccount).where(
                    MailAccount.user_id == LOCAL_USER,
                    MailAccount.source == "gmail",
                )
            )
            if account is not None and account.email != email:
                raise GoogleConnectionError(
                    "기존 연결 계정을 보존했습니다. 계정 변경은 별도 작업입니다"
                )
            credential = (
                session.scalar(
                    select(GoogleCredential)
                    .where(
                        GoogleCredential.account_id == account.account_id,
                    )
                    .with_for_update()
                )
                if account
                else None
            )
            payload = dict(tokens)
            if not payload.get("refresh_token") and credential:
                try:
                    previous = json.loads(
                        self._cipher.decrypt(credential.token_ciphertext.encode())
                    )
                    payload["refresh_token"] = previous["refresh_token"]
                except (InvalidToken, ValueError, KeyError, TypeError):
                    raise GoogleConnectionError(
                        "기존 암호화 키를 확인한 뒤 다시 연결하세요"
                    ) from None
            if not payload.get("refresh_token"):
                raise GoogleConnectionError(
                    "오프라인 접근 권한을 받지 못했습니다. 동의를 다시 진행하세요"
                )
            now = datetime.now(UTC)
            payload["expires_at"] = (now + timedelta(seconds=payload.pop("expires_in"))).isoformat()
            ciphertext = self._cipher.encrypt(json.dumps(payload).encode()).decode()
            if account is None:
                account = MailAccount(
                    account_id=str(uuid4()),
                    user_id=LOCAL_USER,
                    source="gmail",
                    email=email,
                    sync_started_at=now,
                )
                session.add(account)
                session.flush()
            if credential is None:
                session.add(
                    GoogleCredential(
                        account_id=account.account_id, token_ciphertext=ciphertext, updated_at=now
                    )
                )
            else:
                credential.token_ciphertext = ciphertext
                credential.updated_at = now
