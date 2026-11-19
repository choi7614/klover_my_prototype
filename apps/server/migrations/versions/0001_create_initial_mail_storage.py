"""사용자·계정·메일의 초기 저장 구조."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "mail_accounts",
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("sync_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_cursor", sa.Text(), nullable=True),
        sa.CheckConstraint("source IN ('gmail', 'fixture')", name="ck_account_source"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("account_id"),
        sa.UniqueConstraint("account_id", "user_id", name="uq_account_owner"),
        sa.UniqueConstraint("user_id", "source", "email", name="uq_account_owner_source_email"),
    )
    op.create_table(
        "mails",
        sa.Column("mail_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("source_message_id", sa.Text(), nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=True),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("mailbox", sa.String(length=20), server_default="inbox", nullable=False),
        sa.Column("from_addr", sa.Text(), nullable=False),
        sa.Column("from_name", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "to", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "cc", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), server_default="", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "analysis_status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.CheckConstraint(
            "analysis_status IN ('pending', 'done', 'failed')", name="ck_mail_analysis"
        ),
        sa.CheckConstraint("direction IN ('received', 'sent')", name="ck_mail_direction"),
        sa.CheckConstraint(
            "mailbox IN ('inbox', 'sent', 'draft', 'archive', 'spam', 'trash')",
            name="ck_mail_mailbox",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_mail_account_owner",
        ),
        sa.PrimaryKeyConstraint("mail_id"),
        sa.UniqueConstraint("account_id", "source_message_id", name="uq_mail_source_message"),
    )
    op.create_index(
        "ix_mail_owner_received", "mails", ["user_id", "received_at", "mail_id"], unique=False
    )


def downgrade():
    op.drop_index("ix_mail_owner_received", table_name="mails")
    op.drop_table("mails")
    op.drop_table("mail_accounts")
    op.drop_table("users")
