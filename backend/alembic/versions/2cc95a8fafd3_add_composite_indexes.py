"""Add composite indexes for hot query paths.

Revision ID: 2cc95a8fafd3
Revises: 1f9530201111
Create Date: 2026-02-21

Adds:
  - ix_holdings_org_ticker  (organization_id, ticker)  — portfolio queries
  - ix_accounts_org_active  (organization_id, is_active) — account listing
  - ix_accounts_org_type    (organization_id, account_type) — account filtering
"""

from typing import Union
from alembic import op


revision: str = "2cc95a8fafd3"
down_revision: Union[str, None] = "1f9530201111"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_holdings_org_ticker", "holdings", ["organization_id", "ticker"])
    op.create_index("ix_accounts_org_active", "accounts", ["organization_id", "is_active"])
    op.create_index("ix_accounts_org_type",   "accounts", ["organization_id", "account_type"])


def downgrade() -> None:
    op.drop_index("ix_accounts_org_type",   table_name="accounts")
    op.drop_index("ix_accounts_org_active", table_name="accounts")
    op.drop_index("ix_holdings_org_ticker", table_name="holdings")
