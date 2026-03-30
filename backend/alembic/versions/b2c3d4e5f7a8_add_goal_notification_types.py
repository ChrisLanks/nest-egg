"""Add goal_completed and goal_funded notification type enum values.

Revision ID: b2c3d4e5f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30

These values exist in the Python NotificationType enum but were never added
to the PostgreSQL notificationtype enum, causing 500 errors when goals are
completed or funded.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f7a8"
down_revision: Union[str, None] = "r67_add_credit_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'goal_completed'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'goal_funded'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    pass
