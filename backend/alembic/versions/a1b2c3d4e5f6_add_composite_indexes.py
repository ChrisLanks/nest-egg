"""Add composite indexes for common org-scoped queries.

Revision ID: a1b2c3d4e5f6
Revises: 3dd06b9e0f14
Create Date: 2026-02-22 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic
revision = 'a1b2c3d4e5f6'
down_revision = '3dd06b9e0f14'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_holdings_org_ticker',   'holdings',     ['organization_id', 'ticker'])
    op.create_index('ix_accounts_org_active',   'accounts',     ['organization_id', 'is_active'])
    op.create_index('ix_accounts_org_type',     'accounts',     ['organization_id', 'account_type'])
    op.create_index('ix_transactions_org_acct', 'transactions', ['organization_id', 'account_id'])
    op.create_index('ix_transactions_org_cat',  'transactions', ['organization_id', 'category_id'])


def downgrade() -> None:
    op.drop_index('ix_transactions_org_cat',  table_name='transactions')
    op.drop_index('ix_transactions_org_acct', table_name='transactions')
    op.drop_index('ix_accounts_org_type',     table_name='accounts')
    op.drop_index('ix_accounts_org_active',   table_name='accounts')
    op.drop_index('ix_holdings_org_ticker',   table_name='holdings')
