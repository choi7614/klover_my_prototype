"""첫 저장 단위. OAuth 토큰·AI 결과의 쓰기는 후속 단위에서 추가한다."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MailAccount(Base):
    __tablename__ = "mail_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "source", "email", name="uq_account_owner_source_email"),
        UniqueConstraint("account_id", "user_id", name="uq_account_owner"),
        CheckConstraint("source IN ('gmail', 'fixture')", name="ck_account_source"),
    )

    account_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    source: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(Text)
    sync_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sync_cursor: Mapped[str | None] = mapped_column(Text)


class Mail(Base):
    __tablename__ = "mails"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_mail_account_owner",
        ),
        UniqueConstraint("account_id", "source_message_id", name="uq_mail_source_message"),
        CheckConstraint("direction IN ('received', 'sent')", name="ck_mail_direction"),
        CheckConstraint(
            "mailbox IN ('inbox', 'sent', 'draft', 'archive', 'spam', 'trash')",
            name="ck_mail_mailbox",
        ),
        CheckConstraint(
            "analysis_status IN ('pending', 'done', 'failed')", name="ck_mail_analysis"
        ),
        Index("ix_mail_owner_received", "user_id", "received_at", "mail_id"),
    )

    mail_id: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(Text)
    source_message_id: Mapped[str] = mapped_column(Text)
    thread_id: Mapped[str | None] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(String(20))
    mailbox: Mapped[str] = mapped_column(String(20), server_default="inbox")
    from_addr: Mapped[str] = mapped_column(Text)
    from_name: Mapped[str] = mapped_column(Text, server_default="")
    to: Mapped[list[dict]] = mapped_column(JSONB, server_default="[]")
    cc: Mapped[list[dict]] = mapped_column(JSONB, server_default="[]")
    subject: Mapped[str] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text)
    body_html: Mapped[str] = mapped_column(Text, server_default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_read: Mapped[bool] = mapped_column(Boolean, server_default="false")
    analysis_status: Mapped[str] = mapped_column(String(20), server_default="pending")
