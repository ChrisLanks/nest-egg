"""Add expanded notification types.

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2026-03-18

Add ACCOUNT_CONNECTED, HOUSEHOLD_MEMBER_JOINED, HOUSEHOLD_MEMBER_LEFT,
FIRE_COAST_FI, FIRE_INDEPENDENT, and RETIREMENT_SCENARIO_STALE notification types.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r2s3t4u5v6w7"
down_revision: Union[str, None] = "q1r2s3t4u5v6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'ACCOUNT_CONNECTED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'HOUSEHOLD_MEMBER_JOINED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'HOUSEHOLD_MEMBER_LEFT'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'FIRE_COAST_FI'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'FIRE_INDEPENDENT'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'RETIREMENT_SCENARIO_STALE'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # The extra values are harmless if the feature is rolled back.
    pass
