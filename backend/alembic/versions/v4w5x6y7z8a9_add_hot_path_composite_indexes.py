"""Add hot-path composite indexes for notifications, holdings, savings goals, and portfolio snapshots.

Revision ID: s1t2u3v4w5x6
Revises: 8dc2b060f568, d3e4f5a6b7c8, f1a2b3c4d5e6, d345678901cd, r0s1t2u3v4w5
Create Date: 2026-03-12

Adds composite indexes that are missing for frequently-queried paths:

  - ix_notifications_user_unread (organization_id, user_id, is_read)
      Speeds up the unread-notification badge query.

  - ix_holdings_account_ticker (account_id, ticker)
      Speeds up per-account holding lookups and upserts during sync.

  - ix_savings_goals_org_user (organization_id, user_id)
      Speeds up per-user goal listing inside an organization.

  - ix_portfolio_snapshots_org_date (organization_id, snapshot_date DESC)
      Speeds up latest-snapshot and date-range queries for charting.

Skipped (already exist):
  - accounts(organization_id, account_type, is_active)  → idx_accounts_org_type
  - transactions(account_id, date DESC)                  → idx_transactions_account_date
  - transactions(organization_id, date DESC)             → idx_transactions_org_date
  - recurring_transactions(organization_id, is_active)   → ix_recurring_org_active
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "v4w5x6y7z8a9"
down_revision: Union[str, None] = "u3v4w5x6y7z8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Notifications: unread badge per user
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["organization_id", "user_id", "is_read"],
    )

    # Holdings: per-account ticker lookup / upsert
    op.create_index(
        "ix_holdings_account_ticker",
        "holdings",
        ["account_id", "ticker"],
    )

    # Savings goals: per-user listing within an org
    op.create_index(
        "ix_savings_goals_org_user",
        "savings_goals",
        ["organization_id", "user_id"],
    )

    # Portfolio snapshots: latest-snapshot and date-range queries (DESC for newest-first)
    op.create_index(
        "ix_portfolio_snapshots_org_date",
        "portfolio_snapshots",
        ["organization_id", sa.text("snapshot_date DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_snapshots_org_date", table_name="portfolio_snapshots")
    op.drop_index("ix_savings_goals_org_user", table_name="savings_goals")
    op.drop_index("ix_holdings_account_ticker", table_name="holdings")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
