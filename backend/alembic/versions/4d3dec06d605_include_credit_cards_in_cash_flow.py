"""include_credit_cards_in_cash_flow

Revision ID: 4d3dec06d605
Revises: 5cb6670c8f07
Create Date: 2026-02-16 00:42:05.781772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d3dec06d605'
down_revision: Union[str, None] = '5cb6670c8f07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Include credit cards in cash flow calculations
    # We want to see credit card purchases (real spending)
    # Payments to credit cards are filtered via is_transfer flag
    op.execute("""
        UPDATE accounts
        SET exclude_from_cash_flow = FALSE
        WHERE account_type = 'CREDIT_CARD'
    """)


def downgrade() -> None:
    # Revert credit cards back to excluded
    op.execute("""
        UPDATE accounts
        SET exclude_from_cash_flow = TRUE
        WHERE account_type = 'CREDIT_CARD'
    """)
