"""Add missing performance indexes on holdings and savings_goals.

ix_holdings_org_ticker    — price-refresh and symbol lookups by org
ix_holdings_asset_type    — asset-type filtering in insights/rebalancing
ix_holdings_sector        — sector analysis across large portfolios
ix_savings_goals_org_target_date — upcoming-goals sort (target_date ASC)

Revision ID: r80_holding_goal_idx
Revises: r79_notif_covering_idx
Create Date: 2026-04-02
"""

from alembic import op

revision = "r80_holding_goal_idx"
down_revision = "r79_notif_covering_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_holdings_org_ticker", "holdings", ["organization_id", "ticker"])
    op.create_index("ix_holdings_asset_type", "holdings", ["organization_id", "asset_type"])
    op.create_index("ix_holdings_sector", "holdings", ["organization_id", "sector"])
    op.create_index(
        "ix_savings_goals_org_target_date", "savings_goals", ["organization_id", "target_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_savings_goals_org_target_date", table_name="savings_goals")
    op.drop_index("ix_holdings_sector", table_name="holdings")
    op.drop_index("ix_holdings_asset_type", table_name="holdings")
    op.drop_index("ix_holdings_org_ticker", table_name="holdings")
