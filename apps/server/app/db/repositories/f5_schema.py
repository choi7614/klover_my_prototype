"""F5 전용 메타데이터. 공통 Base·모델을 수정하지 않는 적용 전 스키마다."""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.models import Base

metadata = MetaData()
for table in Base.metadata.sorted_tables:
    table.to_metadata(metadata)
if not any(c.name == "uq_mail_f5_owner" for c in metadata.tables["mails"].constraints):
    metadata.tables["mails"].append_constraint(
        UniqueConstraint("mail_id", "user_id", "account_id", name="uq_mail_f5_owner")
    )


class F5Base(DeclarativeBase):
    metadata = metadata


class Suggestion(F5Base):
    __tablename__ = "f5_suggestions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            ["mails.mail_id", "mails.user_id", "mails.account_id"],
            name="fk_f5_suggestion_mail_owner",
        ),
        UniqueConstraint("suggestion_id", "user_id", "account_id", name="uq_f5_suggestion_owner"),
        UniqueConstraint("mail_id", "type", "action_key", name="uq_f5_action"),
        UniqueConstraint("mail_id", "type", "evidence_key", name="uq_f5_evidence"),
        CheckConstraint("type IN ('calendar','todo','reply')", name="ck_f5_type"),
        CheckConstraint("status IN ('pending','approved','dismissed')", name="ck_f5_status"),
        CheckConstraint(
            "execution_status IN ('idle','executing','failed','uncertain',"
            "'blocked','simulated','succeeded')",
            name="ck_f5_execution_status",
        ),
        CheckConstraint("execution_mode IN ('none','test','live','internal')", name="ck_f5_mode"),
        CheckConstraint(
            "status <> 'approved' OR (execution_status = 'succeeded' "
            "AND execution_mode IN ('live','internal') AND result IS NOT NULL)",
            name="ck_f5_real_approval",
        ),
        CheckConstraint("version > 0", name="ck_f5_version"),
        Index("ix_f5_pending", "user_id", "account_id", "status", "created_at", "suggestion_id"),
    )

    suggestion_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    account_id: Mapped[str] = mapped_column(Text)
    mail_id: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    action_key: Mapped[str] = mapped_column(Text)
    evidence_key: Mapped[str] = mapped_column(Text)
    body_sha256: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)
    evidence_spans: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(Text, default="pending")
    execution_status: Mapped[str] = mapped_column(Text, default="idle")
    execution_mode: Mapped[str] = mapped_column(Text, default="none")
    execution_token: Mapped[str | None] = mapped_column(Text)
    execution_payload: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Todo(F5Base):
    __tablename__ = "f5_todos"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            ["mails.mail_id", "mails.user_id", "mails.account_id"],
            name="fk_f5_todo_mail_owner",
        ),
        ForeignKeyConstraint(
            ["suggestion_id", "user_id", "account_id"],
            ["f5_suggestions.suggestion_id", "f5_suggestions.user_id", "f5_suggestions.account_id"],
            name="fk_f5_todo_suggestion_owner",
        ),
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_f5_todo_account_owner",
        ),
        UniqueConstraint("suggestion_id", name="uq_f5_todo_suggestion"),
        UniqueConstraint("user_id", "account_id", "request_id", name="uq_f5_todo_request"),
        CheckConstraint("status IN ('open','completed')", name="ck_f5_todo_status"),
        CheckConstraint("version > 0", name="ck_f5_todo_version"),
        Index("ix_f5_todo_owner", "user_id", "account_id", "created_at", "todo_id"),
    )

    todo_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    account_id: Mapped[str] = mapped_column(Text)
    mail_id: Mapped[str | None] = mapped_column(Text)
    suggestion_id: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(Text)
    request_payload: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    title: Mapped[str] = mapped_column(Text)
    due: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, default="open")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Outbox(F5Base):
    __tablename__ = "f5_suggestion_outbox"
    __table_args__ = (
        ForeignKeyConstraint(
            ["suggestion_id", "user_id", "account_id"],
            ["f5_suggestions.suggestion_id", "f5_suggestions.user_id", "f5_suggestions.account_id"],
            name="fk_f5_outbox_owner",
        ),
        UniqueConstraint("suggestion_id", name="uq_f5_outbox_suggestion"),
    )
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    suggestion_id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(Text)
    account_id: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Dismissal(F5Base):
    __tablename__ = "f5_dismissals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["suggestion_id", "user_id", "account_id"],
            ["f5_suggestions.suggestion_id", "f5_suggestions.user_id", "f5_suggestions.account_id"],
            name="fk_f5_dismissal_owner",
        ),
    )
    suggestion_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    account_id: Mapped[str] = mapped_column(Text)
    dismissed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


F5_TABLES = [Suggestion.__table__, Todo.__table__, Outbox.__table__, Dismissal.__table__]
