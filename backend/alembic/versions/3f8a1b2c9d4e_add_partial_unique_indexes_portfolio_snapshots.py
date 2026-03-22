"""Add missing partial unique indexes to portfolio_snapshots

Revision ID: 3f8a1b2c9d4e
Revises: df3d0a0c3995
Create Date: 2026-03-22

The snapshot_service.py upsert uses ON CONFLICT with partial unique indexes:
  - uq_org_snapshot_date_user    (organization_id, snapshot_date, user_id) WHERE user_id IS NOT NULL
  - uq_org_snapshot_date_household (organization_id, snapshot_date) WHERE user_id IS NULL

These were defined in migration e5f6a7b8c9d0, but that migration was on an
orphaned branch that was never merged into the main chain. Without these indexes
the ON CONFLICT upsert raises InvalidColumnReferenceError in Celery snapshot tasks.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3f8a1b2c9d4e"
down_revision: Union[str, None] = "df3d0a0c3995"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old non-partial unique constraint if it somehow still exists
    op.execute("DROP INDEX IF EXISTS uq_org_snapshot_date")
    # Per-user snapshot: one per (org, date, user)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_org_snapshot_date_user "
        "ON portfolio_snapshots (organization_id, snapshot_date, user_id) "
        "WHERE user_id IS NOT NULL"
    )
    # Household snapshot: one per (org, date) when user_id is NULL
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_org_snapshot_date_household "
        "ON portfolio_snapshots (organization_id, snapshot_date) "
        "WHERE user_id IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_org_snapshot_date_user")
    op.execute("DROP INDEX IF EXISTS uq_org_snapshot_date_household")
