"""저장·조회는 이 저장소를 통해 수행한다. 호출자가 트랜잭션을 관리한다."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Mail, MailAccount, User


class MailRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_user(self, *, user_id: str) -> None:
        self.session.add(User(user_id=user_id))
        self.session.flush()

    def add_account(
        self,
        *,
        account_id: str,
        user_id: str,
        source: str,
        email: str,
        sync_started_at: datetime,
    ) -> None:
        _aware(sync_started_at)
        self.session.add(
            MailAccount(
                account_id=account_id,
                user_id=user_id,
                source=source,
                email=email,
                sync_started_at=sync_started_at,
            )
        )
        self.session.flush()

    def store_received(
        self,
        *,
        user_id: str,
        account_id: str,
        mail_id: str,
        source_message_id: str,
        received_at: datetime,
        from_addr: str,
        subject: str,
        body_text: str,
        from_name: str = "",
        to: list[dict] | None = None,
        thread_id: str | None = None,
    ) -> str | None:
        """사용 시작 이후만 저장한다. 같은 소스 메일의 재시도는 기존 ID를 반환한다."""
        _aware(received_at)
        account = self.session.scalar(
            select(MailAccount).where(
                MailAccount.account_id == account_id,
                MailAccount.user_id == user_id,
            )
        )
        if account is None:
            raise ValueError("지정한 사용자의 메일 아카운트가 없습니다")
        if received_at < account.sync_started_at:
            return None
        statement = (
            insert(Mail)
            .values(
                mail_id=mail_id,
                user_id=user_id,
                account_id=account_id,
                source_message_id=source_message_id,
                received_at=received_at,
                from_addr=from_addr,
                from_name=from_name,
                subject=subject,
                body_text=body_text,
                to=to if to is not None else [],
                thread_id=thread_id,
                direction="received",
            )
            .on_conflict_do_nothing(constraint="uq_mail_source_message")
            .returning(Mail.mail_id)
        )
        saved = self.session.scalar(statement)
        if saved is not None:
            return saved
        return self.session.scalar(
            select(Mail.mail_id).where(
                Mail.account_id == account_id,
                Mail.source_message_id == source_message_id,
                Mail.user_id == user_id,
            )
        )

    def list_received(self, *, user_id: str, limit: int = 50) -> list[Mail]:
        if not 1 <= limit <= 100:
            raise ValueError("조회 개수는 1~100이어야 합니다")
        return list(
            self.session.scalars(
                select(Mail)
                .where(
                    Mail.user_id == user_id,
                    Mail.direction == "received",
                )
                .order_by(Mail.received_at.desc(), Mail.mail_id)
                .limit(limit)
            )
        )


def _aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("시각에는 시간대가 필요합니다")
