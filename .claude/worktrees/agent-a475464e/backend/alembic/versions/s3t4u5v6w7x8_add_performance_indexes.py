"""Add performance indexes for scale.

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-03-18

Add composite and single-column indexes to support common query
patterns at scale: holdings by ticker, snapshots by date,
notifications by type+dismissed, and token expiry cleanup.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "s3t4u5v6w7x8"
down_revision: Union[str, None] = "r2s3t4u5v6w7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Holdings: portfolio aggregation queries GROUP BY ticker
    op.create_index(
        "ix_holdings_org_ticker",
        "holdings",
        ["organization_id", "ticker"],
    )

    # Portfolio snapshots: time-range trend queries
    op.create_index(
        "ix_portfolio_snapshots_org_date",
        "portfolio_snapshots",
        ["organization_id", "snapshot_date"],
    )

    # Net worth snapshots: time-range trend queries
    op.create_index(
        "ix_net_worth_snapshots_org_date",
        "net_worth_snapshots",
        ["organization_id", "snapshot_date"],
    )

    # Notifications: milestone dedup queries (org + type + dismissed)
    op.create_index(
        "ix_notifications_org_type_dismissed",
        "notifications",
        ["organization_id", "type", "is_dismissed"],
    )

    # Token cleanup: daily expired token deletion
    op.create_index(
        "ix_password_reset_tokens_expires",
        "password_reset_tokens",
        ["expires_at"],
    )
    op.create_index(
        "ix_email_verification_tokens_expires",
        "email_verification_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_verification_tokens_expires", "email_verification_tokens")
    op.drop_index("ix_password_reset_tokens_expires", "password_reset_tokens")
    op.drop_index("ix_notifications_org_type_dismissed", "notifications")
    op.drop_index("ix_net_worth_snapshots_org_date", "net_worth_snapshots")
    op.drop_index("ix_portfolio_snapshots_org_date", "portfolio_snapshots")
    op.drop_index("ix_holdings_org_ticker", "holdings")
