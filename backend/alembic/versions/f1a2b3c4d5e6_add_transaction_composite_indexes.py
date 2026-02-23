"""Add transaction composite indexes for common org-scoped queries.

These two indexes were not covered by 2cc95a8fafd3 (which added holdings/accounts
composite indexes). This migration adds the remaining high-value indexes for
transaction queries.

Revision ID: f1a2b3c4d5e6
Revises: 3dd06b9e0f14
Create Date: 2026-02-22 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic
revision = 'f1a2b3c4d5e6'
down_revision = '3dd06b9e0f14'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_transactions_org_acct', 'transactions', ['organization_id', 'account_id'])
    op.create_index('ix_transactions_org_cat',  'transactions', ['organization_id', 'category_id'])


def downgrade() -> None:
    op.drop_index('ix_transactions_org_cat',  table_name='transactions')
    op.drop_index('ix_transactions_org_acct', table_name='transactions')
