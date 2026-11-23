"""최소 메일 저장 구조와 암호화된 Google 토큰. AI 결과는 후속 단위다."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
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


class GoogleCredential(Base):
    __tablename__ = "google_credentials"

    account_id: Mapped[str] = mapped_column(
        ForeignKey("mail_accounts.account_id"), primary_key=True
    )
    token_ciphertext: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Mail(Base):
    __tablename__ = "mails"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_mail_account_owner",
        ),
        UniqueConstraint("account_id", "source_message_id", name="uq_mail_source_message"),
        UniqueConstraint("mail_id", "user_id", "account_id", name="uq_mail_f5_owner"),
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
    history_imported: Mapped[bool] = mapped_column(Boolean, server_default="false")
    analysis_status: Mapped[str] = mapped_column(String(20), server_default="pending")


class WeeklyReportRow(Base):
    """F4 보고서. 소유 계정은 검증된 payload와 선택 키에 함께 저장한다."""

    __tablename__ = "weekly_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "selection_key", name="uq_weekly_report_owner_selection"),
    )

    report_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    selection_key: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class HistoryImportJob(Base):
    __tablename__ = "history_import_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_history_import_owner",
        ),
    )
    job_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    account_id: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
