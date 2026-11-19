"""F3 최근 검색. 기존 사용자·계정·메일은 변경하지 않는다."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_search_runs"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "search_runs",
        sa.Column("search_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("parsed", postgresql.JSONB(), nullable=False),
        sa.Column("overrides", postgresql.JSONB(), nullable=False),
        sa.Column("reference_date", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_search_run_account_owner",
        ),
    )
    op.create_index(
        "ix_search_run_owner_created", "search_runs", ["user_id", "account_id", "created_at"]
    )


def downgrade():
    op.drop_index("ix_search_run_owner_created", table_name="search_runs")
    op.drop_table("search_runs")
