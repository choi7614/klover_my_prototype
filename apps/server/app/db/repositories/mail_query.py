"""로컬 연결 계정만 읽는다. 소유자는 HTTP 입력으로 받지 않는다."""

import base64
import json
import re
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.models import GoogleCredential, Mail, MailAccount
from app.db.repositories.google_connection import LOCAL_USER
from app.schemas.mail_api import LocalSession, MailDetail, MailPage, MailSummary


class MailAccountUnavailable(ValueError):
    pass


class InvalidMailCursor(ValueError):
    pass


def decode_cursor(value: str):
    try:
        if len(value) > 1024 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError
        fields = json.loads(
            base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        )
        if (
            not isinstance(fields, list)
            or len(fields) != 3
            or type(fields[0]) is not int
            or fields[0] != 1
        ):
            raise ValueError
        stamp = datetime.fromisoformat(fields[1])
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError
        if not isinstance(fields[2], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", fields[2]):
            raise ValueError
        return stamp, fields[2]
    except (ValueError, TypeError, KeyError, OverflowError):
        raise InvalidMailCursor("메일 페이지 위치를 확인하세요") from None


def _cursor(mail):
    data = json.dumps([1, mail.received_at.isoformat(), mail.mail_id]).encode()
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _summary(mail):
    return dict(
        mail_id=mail.mail_id,
        subject=mail.subject,
        from_addr=mail.from_addr,
        from_name=mail.from_name,
        preview=mail.body_text[:160],
        received_at=mail.received_at,
        is_read=mail.is_read,
        analysis_status=mail.analysis_status,
    )


class MailQueryRepository:
    def __init__(self, engine, expected_email):
        self.engine, self.expected_email = engine, expected_email

    def _owner(self, session):
        account = session.scalar(
            select(MailAccount)
            .join(
                GoogleCredential,
                GoogleCredential.account_id == MailAccount.account_id,
            )
            .where(
                MailAccount.user_id == LOCAL_USER,
                MailAccount.source == "gmail",
                MailAccount.email == self.expected_email,
            )
        )
        if account is None:
            raise MailAccountUnavailable("연결한 계정을 확인하세요")
        return account

    def session(self):
        with Session(self.engine) as session:
            account = self._owner(session)
            return LocalSession(
                user_id=account.user_id,
                account_id=account.account_id,
                email=account.email,
                sync_started_at=account.sync_started_at,
            )

    def _received(self, account):
        return select(Mail).where(
            Mail.user_id == account.user_id,
            Mail.account_id == account.account_id,
            Mail.direction == "received",
            Mail.mailbox == "inbox",
            Mail.received_at >= account.sync_started_at,
        )

    def list(self, *, limit=20, cursor=None):
        position = decode_cursor(cursor) if cursor else None
        with Session(self.engine) as session:
            account = self._owner(session)
            query = self._received(account)
            if position:
                stamp, identifier = position
                query = query.where(
                    or_(
                        Mail.received_at < stamp,
                        and_(Mail.received_at == stamp, Mail.mail_id < identifier),
                    )
                )
            rows = list(
                session.scalars(
                    query.order_by(Mail.received_at.desc(), Mail.mail_id.desc()).limit(limit + 1)
                )
            )
            more = len(rows) > limit
            rows = rows[:limit]
            return MailPage(
                items=[MailSummary(**_summary(row)) for row in rows],
                next_cursor=_cursor(rows[-1]) if more else None,
            )

    def detail(self, mail_id):
        with Session(self.engine) as session:
            account = self._owner(session)
            row = session.scalar(self._received(account).where(Mail.mail_id == mail_id))
            if row is None:
                return None
            return MailDetail(**_summary(row), to=row.to, cc=row.cc, body_text=row.body_text)
