"""Add covering index for unread notifications dashboard query.

ix_notifications_user_unread_created (user_id, is_read, created_at) replaces
two separate index lookups with a single scan for the most common pattern:
"give me unread notifications for this user, newest first".

Revision ID: r79_notif_covering_idx
Revises: r78_add_settled_at
Create Date: 2026-04-02
"""

from alembic import op

revision = "r79_notif_covering_idx"
down_revision = "r78_add_settled_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_notifications_user_unread_created",
        "notifications",
        ["user_id", "is_read", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_unread_created", table_name="notifications")
