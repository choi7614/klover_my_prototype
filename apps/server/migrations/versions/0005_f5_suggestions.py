"""F5 제안·할 일·알림 outbox를 추가한다. 기존 메일·계정은 보존한다."""

import sqlalchemy as sa
from alembic import op

revision = "0005_f5"
down_revision = "0004_f2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_mail_f5_owner", "mails", ["mail_id", "user_id", "account_id"])
    op.create_table(
        "f5_suggestions",
        sa.Column("suggestion_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("mail_id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("action_key", sa.Text(), nullable=False),
        sa.Column("evidence_key", sa.Text(), nullable=False),
        sa.Column("body_sha256", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("evidence_spans", sa.JSON(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("execution_status", sa.Text(), nullable=False),
        sa.Column("execution_mode", sa.Text(), nullable=False),
        sa.Column("execution_token", sa.Text(), nullable=True),
        sa.Column("execution_payload", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "execution_mode IN ('none','test','live','internal')", name="ck_f5_mode"
        ),
        sa.CheckConstraint(
            "execution_status IN ('idle','executing','failed','uncertain',"
            "'blocked','simulated','succeeded')",
            name="ck_f5_execution_status",
        ),
        sa.CheckConstraint(
            "status <> 'approved' OR (execution_status = 'succeeded' "
            "AND execution_mode IN ('live','internal') AND result IS NOT NULL)",
            name="ck_f5_real_approval",
        ),
        sa.CheckConstraint("status IN ('pending','approved','dismissed')", name="ck_f5_status"),
        sa.CheckConstraint("type IN ('calendar','todo','reply')", name="ck_f5_type"),
        sa.CheckConstraint("version > 0", name="ck_f5_version"),
        sa.ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            ["mails.mail_id", "mails.user_id", "mails.account_id"],
            name="fk_f5_suggestion_mail_owner",
        ),
        sa.PrimaryKeyConstraint("suggestion_id"),
        sa.UniqueConstraint("mail_id", "type", "action_key", name="uq_f5_action"),
        sa.UniqueConstraint("mail_id", "type", "evidence_key", name="uq_f5_evidence"),
        sa.UniqueConstraint(
            "suggestion_id", "user_id", "account_id", name="uq_f5_suggestion_owner"
        ),
    )
    op.create_index(
        "ix_f5_pending",
        "f5_suggestions",
        ["user_id", "account_id", "status", "created_at", "suggestion_id"],
        unique=False,
    )
    op.create_table(
        "f5_dismissals",
        sa.Column("suggestion_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["suggestion_id", "user_id", "account_id"],
            ["f5_suggestions.suggestion_id", "f5_suggestions.user_id", "f5_suggestions.account_id"],
            name="fk_f5_dismissal_owner",
        ),
        sa.PrimaryKeyConstraint("suggestion_id"),
    )
    op.create_table(
        "f5_suggestion_outbox",
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("suggestion_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["suggestion_id", "user_id", "account_id"],
            ["f5_suggestions.suggestion_id", "f5_suggestions.user_id", "f5_suggestions.account_id"],
            name="fk_f5_outbox_owner",
        ),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("suggestion_id", name="uq_f5_outbox_suggestion"),
    )
    op.create_table(
        "f5_todos",
        sa.Column("todo_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("mail_id", sa.Text(), nullable=True),
        sa.Column("suggestion_id", sa.Text(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("request_payload", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("due", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('open','completed')", name="ck_f5_todo_status"),
        sa.CheckConstraint("version > 0", name="ck_f5_todo_version"),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_f5_todo_account_owner",
        ),
        sa.ForeignKeyConstraint(
            ["mail_id", "user_id", "account_id"],
            ["mails.mail_id", "mails.user_id", "mails.account_id"],
            name="fk_f5_todo_mail_owner",
        ),
        sa.ForeignKeyConstraint(
            ["suggestion_id", "user_id", "account_id"],
            ["f5_suggestions.suggestion_id", "f5_suggestions.user_id", "f5_suggestions.account_id"],
            name="fk_f5_todo_suggestion_owner",
        ),
        sa.PrimaryKeyConstraint("todo_id"),
        sa.UniqueConstraint("suggestion_id", name="uq_f5_todo_suggestion"),
        sa.UniqueConstraint("user_id", "account_id", "request_id", name="uq_f5_todo_request"),
    )
    op.create_index(
        "ix_f5_todo_owner",
        "f5_todos",
        ["user_id", "account_id", "created_at", "todo_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_f5_todo_owner", table_name="f5_todos")
    op.drop_table("f5_todos")
    op.drop_table("f5_suggestion_outbox")
    op.drop_table("f5_dismissals")
    op.drop_index("ix_f5_pending", table_name="f5_suggestions")
    op.drop_table("f5_suggestions")
    op.drop_constraint("uq_mail_f5_owner", "mails", type_="unique")
