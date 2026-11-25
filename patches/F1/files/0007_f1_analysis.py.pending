"""F1 분석 결과·본문/요약 벡터·분류 수정 이력. 기존 메일·계정·토큰은 바꾸지 않는다.

integration/F1-mail-analysis/001_storage.sql을 옮긴 이력이다. 차이:
- mails의 (mail_id,user_id,account_id) 유일 제약은 0005의 uq_mail_f5_owner를 재사용한다
  (같은 제약을 중복으로 만들지 않는다).
- 제약·인덱스에 이름을 붙였다(app/db/f1_models.py와 같은 이름).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_f1"
down_revision = "0006_f4"
branch_labels = None
depends_on = None

CATEGORIES = "'work_request','meeting','approval','report_share','notice','external','newsletter'"


class Vector(sa.types.UserDefinedType):
    # 검색 경로(search_path)에 public이 없어도 찾도록 확장을 만든 public 스키마로 지정한다.
    cache_ok = True

    def get_col_spec(self, **_kw):
        return "public.vector"


def upgrade():
    # pgvector가 설치된 DB(infra의 pgvector/pgvector:pg16)에서만 동작한다.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
    op.create_table(
        "f1_mail_analysis",
        sa.Column("mail_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("user_label", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "action_items",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("needs_reply", sa.Boolean(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("priority_reason", sa.Text(), nullable=True),
        sa.Column(
            "entities",
            postgresql.JSONB(),
            server_default=sa.text("""'{"projects":[],"orgs":[],"people":[]}'::jsonb"""),
            nullable=False,
        ),
        sa.Column(
            "events", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column(
            "evidence_spans",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("failure_code", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("llm_provider", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.Text(), nullable=True),
        sa.Column("llm_mode", sa.Text(), nullable=True),
        sa.Column("embedding_provider", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("embedding_mode", sa.Text(), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(f"category IN ({CATEGORIES})", name="ck_f1_analysis_category"),
        sa.CheckConstraint(f"user_label IN ({CATEGORIES})", name="ck_f1_analysis_user_label"),
        sa.CheckConstraint("priority IN ('high','normal','low')", name="ck_f1_analysis_priority"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 2", name="ck_f1_analysis_attempts"),
        sa.CheckConstraint("llm_mode IN ('live','test')", name="ck_f1_analysis_llm_mode"),
        sa.CheckConstraint(
            "embedding_mode IN ('live','test')", name="ck_f1_analysis_embedding_mode"
        ),
        sa.CheckConstraint(
            "embedding_dimensions BETWEEN 1 AND 4096", name="ck_f1_analysis_dimensions"
        ),
        sa.ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            ["mails.mail_id", "mails.user_id", "mails.account_id"],
            name="fk_f1_analysis_mail_owner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("mail_id"),
        sa.UniqueConstraint("mail_id", "user_id", "account_id", name="uq_f1_analysis_owner"),
    )
    op.create_table(
        "f1_mail_chunks",
        sa.Column("chunk_id", sa.Text(), nullable=False),
        sa.Column("mail_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding_provider", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("embedding_mode", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.CheckConstraint("kind IN ('body','summary')", name="ck_f1_chunk_kind"),
        sa.CheckConstraint("seq >= 0", name="ck_f1_chunk_seq"),
        sa.CheckConstraint(
            "embedding_dimensions BETWEEN 1 AND 4096", name="ck_f1_chunk_dimensions"
        ),
        sa.CheckConstraint("embedding_mode IN ('live','test')", name="ck_f1_chunk_embedding_mode"),
        sa.CheckConstraint(f"category IN ({CATEGORIES})", name="ck_f1_chunk_category"),
        sa.CheckConstraint(
            "public.vector_dims(embedding) = embedding_dimensions",
            name="ck_f1_chunk_vector_dims",
        ),
        sa.ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            [
                "f1_mail_analysis.mail_id",
                "f1_mail_analysis.user_id",
                "f1_mail_analysis.account_id",
            ],
            name="fk_f1_chunk_analysis_owner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("chunk_id"),
        sa.UniqueConstraint("mail_id", "kind", "seq", name="uq_f1_chunk_position"),
    )
    op.create_index(
        "ix_f1_chunks_scope",
        "f1_mail_chunks",
        ["user_id", "account_id", "received_at", "category"],
        unique=False,
    )
    op.create_table(
        "f1_category_feedback",
        sa.Column("feedback_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mail_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("from_addr", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("user_label", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(f"user_label IN ({CATEGORIES})", name="ck_f1_feedback_user_label"),
        sa.ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            [
                "f1_mail_analysis.mail_id",
                "f1_mail_analysis.user_id",
                "f1_mail_analysis.account_id",
            ],
            name="fk_f1_feedback_analysis_owner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("feedback_id"),
    )
    op.create_index(
        "ix_f1_feedback_sender",
        "f1_category_feedback",
        ["user_id", "account_id", "from_addr", sa.text("feedback_id DESC")],
        unique=False,
    )


def downgrade():
    # F1 테이블만 지운다. vector 확장과 기존 메일·계정은 남긴다.
    op.drop_index("ix_f1_feedback_sender", table_name="f1_category_feedback")
    op.drop_table("f1_category_feedback")
    op.drop_index("ix_f1_chunks_scope", table_name="f1_mail_chunks")
    op.drop_table("f1_mail_chunks")
    op.drop_table("f1_mail_analysis")
