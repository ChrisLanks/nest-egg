"""Add transaction composite indexes for date+amount, account+merchant, and transfer+date.

These indexes cover common query patterns:
- org+date+amount: income/expense reports, duplicate detection
- org+account+merchant: merchant spending breakdowns per account
- org+is_transfer+date: cash flow queries that exclude transfers

Revision ID: n6o7p8q9r0s1
Revises: m5n6o7p8q9r0
Create Date: 2026-02-24 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n6o7p8q9r0s1"
down_revision: Union[str, None] = "m5n6o7p8q9r0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_org_date_amount",
        "transactions",
        ["organization_id", "date", "amount"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_transactions_org_acct_merchant",
        "transactions",
        ["organization_id", "account_id", "merchant_name"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_transactions_org_transfer_date",
        "transactions",
        ["organization_id", "is_transfer", "date"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_org_transfer_date", table_name="transactions")
    op.drop_index("ix_transactions_org_acct_merchant", table_name="transactions")
    op.drop_index("ix_transactions_org_date_amount", table_name="transactions")
