"""Add household expense-splitting notification type enum values.

Revision ID: r77_household_notif
Revises: r76_member_split
Create Date: 2026-04-02

Adds two new NotificationType values for household expense-split workflows:
  - expense_split_assigned  — a transaction split was assigned to you
  - settlement_reminder     — outstanding balance due between household members
"""

from typing import Sequence, Union

from alembic import op

revision: str = "r77_household_notif"
down_revision: Union[str, None] = "r76_member_split"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'expense_split_assigned'"
    )
    op.execute(
        "ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'settlement_reminder'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    pass
