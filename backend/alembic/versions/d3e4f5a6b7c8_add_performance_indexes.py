"""Add performance indexes for category_primary and price_as_of.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-02-22

Adds two indexes that were missing and cause full-table scans:
- ix_transactions_org_category: speeds up income/expense category filtering
- ix_holdings_price_as_of: speeds up stale-price detection on login
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_org_category",
        "transactions",
        ["organization_id", "category_primary"],
    )
    op.create_index(
        "ix_holdings_price_as_of",
        "holdings",
        ["price_as_of"],
    )


def downgrade() -> None:
    op.drop_index("ix_holdings_price_as_of", table_name="holdings")
    op.drop_index("ix_transactions_org_category", table_name="transactions")
