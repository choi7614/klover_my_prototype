"""로컬 연결 계정만 읽는다. 소유자는 HTTP 입력으로 받지 않는다."""

import base64
import json
import re
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.db.f1_models import MailAnalysisRecord as Analysis
from app.db.models import GoogleCredential, Mail, MailAccount
from app.db.repositories.google_connection import LOCAL_USER
from app.schemas.mail_api import (
    LocalSession,
    MailCategoryCounts,
    MailDetail,
    MailPage,
    MailSummary,
)
from app.schemas.report import MailCategory


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

    @staticmethod
    def _received_where(account):
        return (
            Mail.user_id == account.user_id,
            Mail.account_id == account.account_id,
            Mail.direction == "received",
            Mail.mailbox == "inbox",
            or_(Mail.received_at >= account.sync_started_at, Mail.history_imported.is_(True)),
        )

    @staticmethod
    def _analysis_join():
        return and_(
            Analysis.mail_id == Mail.mail_id,
            Analysis.user_id == Mail.user_id,
            Analysis.account_id == Mail.account_id,
        )

    def _received(self, account, category: MailCategory | None = None):
        query = select(Mail).where(*self._received_where(account))
        if category is not None:
            # 사용자가 고친 분류(user_label)가 있으면 그것을, 없으면 AI 분류를 쓴다.
            query = query.join(Analysis, self._analysis_join()).where(
                func.coalesce(Analysis.user_label, Analysis.category) == category
            )
        return query

    def category_counts(self):
        with Session(self.engine) as session:
            account = self._owner(session)
            where = self._received_where(account)
            total = session.scalar(select(func.count()).select_from(Mail).where(*where)) or 0
            effective = func.coalesce(Analysis.user_label, Analysis.category)
            rows = session.execute(
                select(effective, func.count())
                .select_from(Mail)
                .join(Analysis, self._analysis_join())
                .where(*where)
                .group_by(effective)
            )
            counts = {name: count for name, count in rows if name is not None}
            return MailCategoryCounts(total=total, counts=counts)

    def list(self, *, limit=20, cursor=None, category: MailCategory | None = None):
        position = decode_cursor(cursor) if cursor else None
        with Session(self.engine) as session:
            account = self._owner(session)
            query = self._received(account, category)
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
