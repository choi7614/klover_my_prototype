"""F5 Calendar 자격 증명만 별도 저장. Gmail 행은 변경하지 않는다."""

import sqlalchemy as sa
from alembic import op

revision = "0009_f5_calendar"
down_revision = "0008_history"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "f5_calendar_credentials",
        sa.Column(
            "account_id", sa.Text(), sa.ForeignKey("mail_accounts.account_id"), primary_key=True
        ),
        sa.Column("token_ciphertext", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("f5_calendar_credentials")
