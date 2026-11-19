"""F2 전용 metadata. 공통 Base와 Alembic 이력에는 자동 등록하지 않는다."""

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.models import User


class F2Base(DeclarativeBase):
    pass


class ProfileRecord(F2Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("formality BETWEEN 0 AND 100", name="ck_profile_formality"),
        CheckConstraint("reply_length IN ('short', 'normal', 'long')", name="ck_profile_length"),
        CheckConstraint("report_style IN ('bullet', 'prose')", name="ck_profile_report_style"),
        CheckConstraint("version >= 1", name="ck_profile_version"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey(User.user_id), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    org: Mapped[str] = mapped_column(Text)
    duties: Mapped[str] = mapped_column(Text)
    frequent_contacts: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    formality: Mapped[int] = mapped_column(Integer)
    reply_length: Mapped[str] = mapped_column(Text)
    greeting: Mapped[str] = mapped_column(Text)
    closing: Mapped[str] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(Text)
    style_learning_enabled: Mapped[bool] = mapped_column(Boolean)
    excluded_phrases: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    report_sections: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    report_recipient: Mapped[str] = mapped_column(Text)
    report_style: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer)


class StyleRecord(F2Base):
    __tablename__ = "style_learnings"

    user_id: Mapped[str] = mapped_column(ForeignKey(User.user_id), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))


class DraftRecord(F2Base):
    __tablename__ = "drafts"
    __table_args__ = (CheckConstraint("version >= 1", name="ck_draft_version"),)

    draft_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(User.user_id), index=True)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    version: Mapped[int] = mapped_column(Integer)
