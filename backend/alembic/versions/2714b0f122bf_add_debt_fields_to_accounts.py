"""add_debt_fields_to_accounts

Revision ID: 2714b0f122bf
Revises: 5463d978066d
Create Date: 2026-02-16 00:16:19.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2714b0f122bf'
down_revision: Union[str, None] = '5463d978066d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add debt-related fields to accounts table
    op.add_column('accounts', sa.Column('interest_rate', sa.Numeric(5, 2), nullable=True))
    op.add_column('accounts', sa.Column('interest_rate_type', sa.String(20), nullable=True))
    op.add_column('accounts', sa.Column('original_amount', sa.Numeric(15, 2), nullable=True))
    op.add_column('accounts', sa.Column('origination_date', sa.Date(), nullable=True))
    op.add_column('accounts', sa.Column('maturity_date', sa.Date(), nullable=True))
    op.add_column('accounts', sa.Column('minimum_payment', sa.Numeric(10, 2), nullable=True))
    op.add_column('accounts', sa.Column('payment_due_day', sa.Integer(), nullable=True))
    op.add_column('accounts', sa.Column('loan_term_months', sa.Integer(), nullable=True))

    # Create index for debt accounts with interest rates
    op.execute("""
        CREATE INDEX ix_accounts_debt_with_rate
        ON accounts(organization_id, account_type, interest_rate)
        WHERE account_type IN ('CREDIT_CARD', 'LOAN', 'student_loan', 'MORTGAGE')
    """)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_accounts_debt_with_rate', 'accounts')

    # Drop columns
    op.drop_column('accounts', 'loan_term_months')
    op.drop_column('accounts', 'payment_due_day')
    op.drop_column('accounts', 'minimum_payment')
    op.drop_column('accounts', 'maturity_date')
    op.drop_column('accounts', 'origination_date')
    op.drop_column('accounts', 'original_amount')
    op.drop_column('accounts', 'interest_rate_type')
    op.drop_column('accounts', 'interest_rate')
