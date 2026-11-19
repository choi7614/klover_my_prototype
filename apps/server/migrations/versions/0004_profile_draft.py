"""기존 사용자·계정·메일·키는 보존하고 F2 테이블만 추가한다."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_f2"
down_revision = "0003_search_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("org", sa.Text(), nullable=False),
        sa.Column("duties", sa.Text(), nullable=False),
        sa.Column("frequent_contacts", postgresql.JSONB(), nullable=False),
        sa.Column("formality", sa.Integer(), nullable=False),
        sa.Column("reply_length", sa.Text(), nullable=False),
        sa.Column("greeting", sa.Text(), nullable=False),
        sa.Column("closing", sa.Text(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("style_learning_enabled", sa.Boolean(), nullable=False),
        sa.Column("excluded_phrases", postgresql.JSONB(), nullable=False),
        sa.Column("report_sections", postgresql.JSONB(), nullable=False),
        sa.Column("report_recipient", sa.Text(), nullable=False),
        sa.Column("report_style", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("formality BETWEEN 0 AND 100", name="ck_profile_formality"),
        sa.CheckConstraint("reply_length IN ('short', 'normal', 'long')", name="ck_profile_length"),
        sa.CheckConstraint("report_style IN ('bullet', 'prose')", name="ck_profile_report_style"),
        sa.CheckConstraint("version >= 1", name="ck_profile_version"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "style_learnings",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "drafts",
        sa.Column("draft_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_draft_version"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("draft_id"),
    )
    op.create_index("ix_drafts_user_id", "drafts", ["user_id"])


def downgrade():
    op.drop_index("ix_drafts_user_id", table_name="drafts")
    op.drop_table("drafts")
    op.drop_table("style_learnings")
    op.drop_table("profiles")
