"""Add user_id to portfolio_snapshots for per-user filtering.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-14

Add nullable user_id column (FK to users.id) and update unique constraint
from (organization_id, snapshot_date) to (organization_id, snapshot_date, user_id).
NULL user_id means whole-household snapshot.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"  # pragma: allowlist secret
down_revision: Union[str, None] = "d4e5f6a7b8c9"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable user_id column
    op.add_column(
        "portfolio_snapshots",
        sa.Column("user_id", PGUUID(as_uuid=True), nullable=True),
    )
    # Add foreign key to users table
    op.create_foreign_key(
        "fk_portfolio_snapshots_user_id",
        "portfolio_snapshots",
        "users",
        ["user_id"],
        ["id"],
    )
    # Drop old unique constraint
    op.drop_constraint("uq_org_snapshot_date", "portfolio_snapshots", type_="unique")
    # Create new unique constraint including user_id (NULLs are distinct in PG
    # by default, so we use a partial unique index instead for proper NULL handling)
    op.execute(
        "CREATE UNIQUE INDEX uq_org_snapshot_date_user "
        "ON portfolio_snapshots (organization_id, snapshot_date, user_id) "
        "WHERE user_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_org_snapshot_date_household "
        "ON portfolio_snapshots (organization_id, snapshot_date) "
        "WHERE user_id IS NULL"
    )
    # Add index on user_id for faster per-user queries
    op.create_index("ix_portfolio_snapshots_user_id", "portfolio_snapshots", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_snapshots_user_id", table_name="portfolio_snapshots")
    op.execute("DROP INDEX IF EXISTS uq_org_snapshot_date_user")
    op.execute("DROP INDEX IF EXISTS uq_org_snapshot_date_household")
    op.drop_constraint(
        "fk_portfolio_snapshots_user_id", "portfolio_snapshots", type_="foreignkey"
    )
    op.drop_column("portfolio_snapshots", "user_id")
    # Restore original unique constraint
    op.create_unique_constraint(
        "uq_org_snapshot_date",
        "portfolio_snapshots",
        ["organization_id", "snapshot_date"],
    )
