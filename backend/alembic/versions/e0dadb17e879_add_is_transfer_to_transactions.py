"""add_is_transfer_to_transactions

Revision ID: e0dadb17e879
Revises: a1d96ed9c8c4
Create Date: 2026-02-15 14:06:12.970315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0dadb17e879'
down_revision: Union[str, None] = 'a1d96ed9c8c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_transfer column (default False)
    op.add_column('transactions', sa.Column('is_transfer', sa.Boolean(), nullable=False, server_default='false'))

    # Auto-detect transfers based on category patterns
    # These are common Plaid categories for transfers
    op.execute("""
        UPDATE transactions
        SET is_transfer = true
        WHERE category_primary IN (
            'TRANSFER_IN',
            'TRANSFER_OUT',
            'Transfer',
            'Bank Transfers',
            'PAYMENT',
            'Credit Card Payment',
            'Payroll Deductions',
            'Third Party'
        )
        OR category_primary ILIKE '%transfer%'
        OR category_primary ILIKE '%payment%'
        OR description ILIKE '%transfer%'
        OR description ILIKE '%payment to%'
    """)


def downgrade() -> None:
    op.drop_column('transactions', 'is_transfer')
