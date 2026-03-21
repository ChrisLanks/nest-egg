"""Add composite indexes for query performance

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-16

Adds composite indexes on frequently-filtered column combinations that
only had individual single-column indexes.  Targets the hottest query
patterns: household-view account resolution, snapshot history by user,
dividend income listing, permission checks, and open tax-lot enumeration.
"""

from alembic import op

revision = "g7h8i9j0k1l2"  # pragma: allowlist secret
down_revision = "f6a7b8c9d0e1"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade() -> None:
    # accounts: household-view resolves user -> active accounts constantly
    op.create_index(
        "ix_accounts_user_org_active",
        "accounts",
        ["user_id", "organization_id", "is_active"],
    )

    # net_worth_snapshots: per-member chart loads sort by date DESC
    op.create_index(
        "ix_nw_snapshots_org_user_date",
        "net_worth_snapshots",
        ["organization_id", "user_id", "snapshot_date"],
    )

    # portfolio_snapshots: per-member investment performance
    op.create_index(
        "ix_portfolio_snapshots_user_date",
        "portfolio_snapshots",
        ["user_id", "snapshot_date"],
    )

    # dividend_income: income history by account + date range
    op.create_index(
        "ix_dividend_income_org_account_paydate",
        "dividend_income",
        ["organization_id", "account_id", "pay_date"],
    )

    # tax_lots: open-lot queries for cost basis / tax-loss harvesting
    op.create_index(
        "ix_tax_lots_account_closed",
        "tax_lots",
        ["account_id", "is_closed"],
    )

    # permission_grants: access-control checks on every household request
    op.create_index(
        "ix_grants_org_grantee_active",
        "permission_grants",
        ["organization_id", "grantee_id", "is_active"],
    )

    # household_guests: filter active guests per org
    op.create_index(
        "ix_household_guests_org_active",
        "household_guests",
        ["organization_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_household_guests_org_active", table_name="household_guests")
    op.drop_index("ix_grants_org_grantee_active", table_name="permission_grants")
    op.drop_index("ix_tax_lots_account_closed", table_name="tax_lots")
    op.drop_index("ix_dividend_income_org_account_paydate", table_name="dividend_income")
    op.drop_index("ix_portfolio_snapshots_user_date", table_name="portfolio_snapshots")
    op.drop_index("ix_nw_snapshots_org_user_date", table_name="net_worth_snapshots")
    op.drop_index("ix_accounts_user_org_active", table_name="accounts")
