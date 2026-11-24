"""F1 분석·청크·분류 피드백 metadata. Alembic 0007_f1과 같은 구조다.

공통 Base에 자동 등록하지 않는다. env.py·공통 비교 검사에서 F5Base.metadata 대신
이 metadata를 쓰게 하는 일은 통합 채팅이 patches/F1/01-database.patch로 한다.
저장소는 SQL로 읽고 쓰며 이 정의는 이력 비교용이다.
mails 쪽 (mail_id,user_id,account_id) 유일 제약은 기존 uq_mail_f5_owner를 재사용한다.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.db.repositories.f5_calendar import CalendarCredential  # noqa: F401
from app.db.repositories.f5_schema import F5Base

CATEGORIES = "'work_request','meeting','approval','report_share','notice','external','newsletter'"


class Vector(UserDefinedType):
    """pgvector의 차원 미고정 vector. 차원은 embedding_dimensions 검사로 맞춘다."""

    cache_ok = True

    def get_col_spec(self, **_kw):
        return "vector"


# 공통·F5 테이블(mails 등)을 복사해 FK를 해석한다. F5가 공통 Base를 복사한 방식과 같다.
# 비교 검사와 env.py는 F5Base.metadata 대신 이 metadata를 쓴다(F5 테이블 포함).
metadata = MetaData()
for table in F5Base.metadata.sorted_tables:
    table.to_metadata(metadata)

# 반영된 DB를 읽을 때 vector 형식을 알아보게 한다(비교 검사의 '모르는 형식' 경고 방지).
for name in ("vector", "public.vector"):
    ischema_names.setdefault(name, Vector)


class F1Base(DeclarativeBase):
    metadata = metadata


class MailAnalysisRecord(F1Base):
    __tablename__ = "f1_mail_analysis"
    __table_args__ = (
        UniqueConstraint("mail_id", "user_id", "account_id", name="uq_f1_analysis_owner"),
        ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            ["mails.mail_id", "mails.user_id", "mails.account_id"],
            name="fk_f1_analysis_mail_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint(f"category IN ({CATEGORIES})", name="ck_f1_analysis_category"),
        CheckConstraint(f"user_label IN ({CATEGORIES})", name="ck_f1_analysis_user_label"),
        CheckConstraint("priority IN ('high','normal','low')", name="ck_f1_analysis_priority"),
        CheckConstraint("attempts BETWEEN 0 AND 2", name="ck_f1_analysis_attempts"),
        CheckConstraint("llm_mode IN ('live','test')", name="ck_f1_analysis_llm_mode"),
        CheckConstraint("embedding_mode IN ('live','test')", name="ck_f1_analysis_embedding_mode"),
        CheckConstraint(
            "embedding_dimensions BETWEEN 1 AND 4096", name="ck_f1_analysis_dimensions"
        ),
    )

    mail_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    account_id: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    user_label: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    action_items: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    needs_reply: Mapped[bool | None] = mapped_column(Boolean)
    priority: Mapped[str | None] = mapped_column(Text)
    priority_reason: Mapped[str | None] = mapped_column(Text)
    entities: Mapped[dict] = mapped_column(
        JSONB, server_default=text("""'{"projects":[],"orgs":[],"people":[]}'::jsonb""")
    )
    events: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    evidence_spans: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    failure_code: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    llm_provider: Mapped[str | None] = mapped_column(Text)
    llm_model: Mapped[str | None] = mapped_column(Text)
    llm_mode: Mapped[str | None] = mapped_column(Text)
    embedding_provider: Mapped[str | None] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(Text)
    embedding_mode: Mapped[str | None] = mapped_column(Text)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MailChunkRecord(F1Base):
    __tablename__ = "f1_mail_chunks"
    __table_args__ = (
        UniqueConstraint("mail_id", "kind", "seq", name="uq_f1_chunk_position"),
        ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            [
                "f1_mail_analysis.mail_id",
                "f1_mail_analysis.user_id",
                "f1_mail_analysis.account_id",
            ],
            name="fk_f1_chunk_analysis_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint("kind IN ('body','summary')", name="ck_f1_chunk_kind"),
        CheckConstraint("seq >= 0", name="ck_f1_chunk_seq"),
        CheckConstraint("embedding_dimensions BETWEEN 1 AND 4096", name="ck_f1_chunk_dimensions"),
        CheckConstraint("embedding_mode IN ('live','test')", name="ck_f1_chunk_embedding_mode"),
        CheckConstraint(f"category IN ({CATEGORIES})", name="ck_f1_chunk_category"),
        CheckConstraint(
            "vector_dims(embedding) = embedding_dimensions", name="ck_f1_chunk_vector_dims"
        ),
        Index("ix_f1_chunks_scope", "user_id", "account_id", "received_at", "category"),
    )

    chunk_id: Mapped[str] = mapped_column(Text, primary_key=True)
    mail_id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(Text)
    account_id: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    seq: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[object] = mapped_column(Vector())
    embedding_dimensions: Mapped[int] = mapped_column(Integer)
    embedding_provider: Mapped[str] = mapped_column(Text)
    embedding_model: Mapped[str] = mapped_column(Text)
    embedding_mode: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    category: Mapped[str] = mapped_column(Text)


class CategoryFeedbackRecord(F1Base):
    __tablename__ = "f1_category_feedback"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            [
                "f1_mail_analysis.mail_id",
                "f1_mail_analysis.user_id",
                "f1_mail_analysis.account_id",
            ],
            name="fk_f1_feedback_analysis_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint(f"user_label IN ({CATEGORIES})", name="ck_f1_feedback_user_label"),
        Index(
            "ix_f1_feedback_sender",
            "user_id",
            "account_id",
            "from_addr",
            text("feedback_id DESC"),
        ),
    )

    feedback_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mail_id: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(Text)
    account_id: Mapped[str] = mapped_column(Text)
    from_addr: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    user_label: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
