"""Add missing notification type enum values.

Revision ID: a1b2c3d4e5f6
Revises: f5d3cbf4ac4d
Create Date: 2026-03-25

Adds enum values that exist in the Python NotificationType model but were
never added to the PostgreSQL notificationtype enum. Without these, any
POST /notifications/ with one of these types returns a 500.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "z9a8b7c6d5e4"
down_revision: Union[str, None] = "f5d3cbf4ac4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'EQUITY_AMT_WARNING'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'HSA_CONTRIBUTION_LIMIT'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'BOND_MATURITY_UPCOMING'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'BENEFICIARY_MISSING'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'TAX_BUCKET_IMBALANCE'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'HARVEST_OPPORTUNITY'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'PRO_RATA_WARNING'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'RMD_TAX_BOMB_WARNING'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'BILL_DUE_BEFORE_PAYCHECK'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'PENSION_ELECTION_DEADLINE'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'REBALANCE_DRIFT_ALERT'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'QCD_OPPORTUNITY'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'NAV_FEATURE_UNLOCKED'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    pass
