"""Add composite indexes for transactions and recurring_transactions.

Revision ID: 513b8ec9f6cc
Revises: f6b305534438
Create Date: 2026-03-19

Adds two composite indexes that are critical for query performance at scale:

1. ix_transactions_org_acct_date — covers the common "all transactions for
   a specific account within a date range" query pattern used by pagination,
   NLP search, and account history endpoints.

2. ix_recurring_org_active_next_date — covers the scheduled-task and
   calendar queries that filter active recurring items and sort/filter by
   next_expected_date.

Both use CONCURRENTLY so they can be created without a table lock on
production. Alembic wraps CREATE INDEX in a transaction by default so we
disable that here.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "513b8ec9f6cc"  # pragma: allowlist secret
down_revision: Union[str, tuple, None] = "f6b305534438"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Disable autocommit wrapper so CONCURRENTLY works (requires no open transaction)
    op.execute("COMMIT")
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_transactions_org_acct_date "
        "ON transactions (organization_id, account_id, date)"
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_recurring_org_active_next_date "
        "ON recurring_transactions (organization_id, is_active, next_expected_date)"
    )


def downgrade() -> None:
    op.execute("COMMIT")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_transactions_org_acct_date")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_recurring_org_active_next_date")
