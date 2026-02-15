"""add_exclude_from_cash_flow_to_accounts

Revision ID: a1d96ed9c8c4
Revises: d345678901cd
Create Date: 2026-02-15 13:51:41.386623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1d96ed9c8c4'
down_revision: Union[str, None] = 'd345678901cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add exclude_from_cash_flow column (default False)
    op.add_column('accounts', sa.Column('exclude_from_cash_flow', sa.Boolean(), nullable=False, server_default='false'))

    # Set default to True for loan/mortgage accounts to prevent double-counting
    # These accounts show balance changes, but payments come from checking/savings
    op.execute("""
        UPDATE accounts
        SET exclude_from_cash_flow = true
        WHERE account_type IN ('MORTGAGE', 'LOAN', 'student_loan', 'CREDIT_CARD')
    """)


def downgrade() -> None:
    op.drop_column('accounts', 'exclude_from_cash_flow')
