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
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'equity_amt_warning'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'hsa_contribution_limit'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'bond_maturity_upcoming'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'beneficiary_missing'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'tax_bucket_imbalance'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'harvest_opportunity'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'pro_rata_warning'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'rmd_tax_bomb_warning'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'bill_due_before_paycheck'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'pension_election_deadline'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'rebalance_drift_alert'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'qcd_opportunity'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'nav_feature_unlocked'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    pass
