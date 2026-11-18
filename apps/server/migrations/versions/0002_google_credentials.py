"""기존 메일을 보존하며 암호화된 Google 토큰 저장소를 추가한다."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "google_credentials",
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("token_ciphertext", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["mail_accounts.account_id"]),
        sa.PrimaryKeyConstraint("account_id"),
    )


def downgrade():
    op.drop_table("google_credentials")
