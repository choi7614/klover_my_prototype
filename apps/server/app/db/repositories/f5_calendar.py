"""Gmail 자격 증명을 덮어쓰지 않는 Calendar 전용 암호화 저장소."""

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import ForeignKey, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.connectors.google_calendar import SCOPES
from app.db.models import MailAccount
from app.db.repositories.f5_schema import F5Base
from app.db.repositories.google_connection import LOCAL_USER, GoogleConnectionRepository
from app.google_config import GoogleConnectionError
from app.services.f5_errors import CalendarError


class CalendarCredential(F5Base):
    __tablename__ = "f5_calendar_credentials"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("mail_accounts.account_id"), primary_key=True
    )
    token_ciphertext: Mapped[str] = mapped_column(Text)


class CalendarConnectionRepository(GoogleConnectionRepository):
    def _account(self, session, owner=None):
        rows = session.scalars(
            select(MailAccount).where(
                MailAccount.user_id == (owner.user_id if owner else LOCAL_USER),
                MailAccount.source == "gmail",
                *([MailAccount.account_id == owner.account_id] if owner else []),
            )
        ).all()
        if len(rows) != 1:
            raise CalendarError("calendar_owner_mismatch", blocked=True)
        return rows[0]

    def email(self, owner):
        with Session(self.engine) as session:
            return self._account(session, owner).email

    def save(self, email, tokens):
        # OAuth의 Gmail profile 확인에 더해 이미 연결된 DB 계정도 일치해야 한다.
        with Session(self.engine) as session, session.begin():
            account = self._account(session)
            if account.email != email:
                raise GoogleConnectionError("기존 Gmail 계정과 같은 계정을 선택하세요")
            row = session.get(CalendarCredential, account.account_id, with_for_update=True)
            payload = dict(tokens)
            if not SCOPES <= set(payload.get("scope", "").split()):
                raise GoogleConnectionError("Calendar 추가 권한을 모두 허용해야 합니다")
            if not payload.get("refresh_token") and row:
                payload["refresh_token"] = json.loads(
                    self._cipher.decrypt(row.token_ciphertext.encode())
                )["refresh_token"]
            if not payload.get("refresh_token"):
                raise GoogleConnectionError("Calendar 오프라인 동의를 다시 확인하세요")
            payload["expires_at"] = (
                datetime.now(UTC) + timedelta(seconds=payload.pop("expires_in"))
            ).isoformat()
            encoded = self._cipher.encrypt(json.dumps(payload).encode()).decode()
            if row:
                row.token_ciphertext = encoded
            else:
                session.add(
                    CalendarCredential(account_id=account.account_id, token_ciphertext=encoded)
                )

    def read(self, owner):
        with Session(self.engine) as session:
            self._account(session, owner)
            row = session.get(CalendarCredential, owner.account_id)
            if row is None:
                raise CalendarError("calendar_not_connected", blocked=True)
            try:
                return json.loads(self._cipher.decrypt(row.token_ciphertext.encode()))
            except Exception:
                raise CalendarError("calendar_connection_failed", blocked=True) from None

    def refresh(self, owner, settings, transport=None):
        import httpx

        # 같은 계정의 갱신·해제를 직렬화한다. Gmail 행에는 쓰지 않는다.
        with Session(self.engine) as session, session.begin():
            self._account(session, owner)
            row = session.get(CalendarCredential, owner.account_id, with_for_update=True)
            if row is None:
                raise CalendarError("calendar_not_connected", blocked=True)
            try:
                previous = json.loads(self._cipher.decrypt(row.token_ciphertext.encode()))
                if datetime.fromisoformat(previous["expires_at"]) > datetime.now(UTC) + timedelta(
                    seconds=60
                ):
                    return previous
                with httpx.Client(
                    timeout=15, trust_env=False, follow_redirects=False, transport=transport
                ) as client:
                    response = client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": settings.client_id,
                            "client_secret": settings.client_secret,
                            "grant_type": "refresh_token",
                            "refresh_token": previous["refresh_token"],
                        },
                    )
                if response.status_code in {400, 401, 403}:
                    raise CalendarError("calendar_permission_expired", blocked=True)
                response.raise_for_status()
                data = response.json()
                if not SCOPES <= set(data.get("scope", previous["scope"]).split()):
                    raise CalendarError("calendar_scope_required", blocked=True)
                if (
                    not isinstance(data["access_token"], str)
                    or not data["access_token"]
                    or len(data["access_token"]) > 16384
                    or type(data["expires_in"]) is not int
                    or not 0 < data["expires_in"] <= 86400
                    or data.get("token_type", "").lower() != "bearer"
                ):
                    raise ValueError
                previous.update(
                    access_token=data["access_token"],
                    scope=data.get("scope", previous["scope"]),
                    expires_at=(
                        datetime.now(UTC) + timedelta(seconds=data["expires_in"])
                    ).isoformat(),
                )
                if data.get("refresh_token"):
                    if (
                        not isinstance(data["refresh_token"], str)
                        or len(data["refresh_token"]) > 16384
                    ):
                        raise ValueError
                    previous["refresh_token"] = data["refresh_token"]
                row.token_ciphertext = self._cipher.encrypt(json.dumps(previous).encode()).decode()
                return previous
            except CalendarError:
                raise
            except Exception:
                raise CalendarError("calendar_connection_failed", blocked=True) from None

    def disconnect(self, owner):
        # Google revoke는 Gmail 권한까지 취소할 수 있다. 로컬 Calendar 토큰만 제거한다.
        with Session(self.engine) as session, session.begin():
            self._account(session, owner)
            row = session.get(CalendarCredential, owner.account_id, with_for_update=True)
            if row:
                session.delete(row)
