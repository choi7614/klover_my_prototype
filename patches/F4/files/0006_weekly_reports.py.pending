"""F4 보고서 스냅샷. 기존 메일·계정·키는 변경하지 않는다."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_f4"
down_revision = "0005_f5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "weekly_reports",
        sa.Column("report_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("selection_key", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("report_id"),
        sa.UniqueConstraint("user_id", "selection_key", name="uq_weekly_report_owner_selection"),
    )


def downgrade():
    op.drop_table("weekly_reports")
