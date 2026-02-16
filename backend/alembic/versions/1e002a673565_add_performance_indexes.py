"""add_performance_indexes

Revision ID: 1e002a673565
Revises: 7dcc04e9aba7
Create Date: 2026-02-16 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e002a673565'
down_revision: Union[str, None] = '7dcc04e9aba7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Critical transaction indexes for performance
    op.create_index(
        'idx_transactions_org_date',
        'transactions',
        ['organization_id', sa.text('date DESC')],
        unique=False
    )
    op.create_index(
        'idx_transactions_org_amount',
        'transactions',
        ['organization_id', 'amount'],
        unique=False
    )
    op.create_index(
        'idx_transactions_org_merchant',
        'transactions',
        ['organization_id', 'merchant_name'],
        unique=False
    )
    op.create_index(
        'idx_transactions_org_category',
        'transactions',
        ['organization_id', 'category_primary'],
        unique=False
    )
    op.create_index(
        'idx_transactions_account_date',
        'transactions',
        ['account_id', sa.text('date DESC')],
        unique=False
    )

    # Label filtering indexes
    op.create_index(
        'idx_transaction_labels_transaction',
        'transaction_labels',
        ['transaction_id'],
        unique=False
    )
    op.create_index(
        'idx_transaction_labels_label',
        'transaction_labels',
        ['label_id'],
        unique=False
    )

    # Budget queries
    op.create_index(
        'idx_budgets_org_active',
        'budgets',
        ['organization_id', 'is_active'],
        unique=False
    )

    # Recurring transaction detection
    op.create_index(
        'idx_transactions_merchant_date',
        'transactions',
        ['merchant_name', sa.text('date DESC')],
        unique=False
    )

    # Account queries
    op.create_index(
        'idx_accounts_org_type',
        'accounts',
        ['organization_id', 'account_type', 'is_active'],
        unique=False
    )

    # Category lookups
    op.create_index(
        'idx_categories_org_name',
        'categories',
        ['organization_id', 'name'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('idx_categories_org_name', table_name='categories')
    op.drop_index('idx_accounts_org_type', table_name='accounts')
    op.drop_index('idx_transactions_merchant_date', table_name='transactions')
    op.drop_index('idx_budgets_org_active', table_name='budgets')
    op.drop_index('idx_transaction_labels_label', table_name='transaction_labels')
    op.drop_index('idx_transaction_labels_transaction', table_name='transaction_labels')
    op.drop_index('idx_transactions_account_date', table_name='transactions')
    op.drop_index('idx_transactions_org_category', table_name='transactions')
    op.drop_index('idx_transactions_org_merchant', table_name='transactions')
    op.drop_index('idx_transactions_org_amount', table_name='transactions')
    op.drop_index('idx_transactions_org_date', table_name='transactions')
