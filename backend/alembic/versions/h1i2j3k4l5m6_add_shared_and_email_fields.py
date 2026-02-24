"""Add shared budget/goal fields and email notification preference.

Revision ID: h1i2j3k4l5m6
Revises: f2a3b4c5d6e7
Create Date: 2026-02-24 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "h1i2j3k4l5m6"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Shared budget fields
    op.add_column("budgets", sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("budgets", sa.Column("shared_user_ids", sa.JSON(), nullable=True))

    # Shared savings goal fields
    op.add_column("savings_goals", sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("savings_goals", sa.Column("shared_user_ids", sa.JSON(), nullable=True))

    # Email notification preference on users
    op.add_column("users", sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("users", "email_notifications_enabled")
    op.drop_column("savings_goals", "shared_user_ids")
    op.drop_column("savings_goals", "is_shared")
    op.drop_column("budgets", "shared_user_ids")
    op.drop_column("budgets", "is_shared")
