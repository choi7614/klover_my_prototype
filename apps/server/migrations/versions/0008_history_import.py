"""명시적 과거 메일과 중단·재개 가능한 작업. 기존 메일은 기본 false로 보존한다."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_history"
down_revision = "0007_f1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "mails",
        sa.Column("history_imported", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "history_import_jobs",
        sa.Column("job_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_history_import_owner",
        ),
    )


def downgrade():
    op.drop_table("history_import_jobs")
    op.drop_column("mails", "history_imported")
