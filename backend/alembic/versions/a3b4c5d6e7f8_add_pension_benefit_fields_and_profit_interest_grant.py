"""add_pension_benefit_fields_and_profit_interest_grant

Revision ID: a3b4c5d6e7f8
Revises: 5bd74cf48dc5
Create Date: 2026-02-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = '5bd74cf48dc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add pension/annuity income fields
    op.add_column('accounts', sa.Column('monthly_benefit', sa.Numeric(10, 2), nullable=True))
    op.add_column('accounts', sa.Column('benefit_start_date', sa.Date(), nullable=True))

    # Add 'profit_interest' to the granttype enum
    # PostgreSQL requires special handling to add enum values
    op.execute("ALTER TYPE granttype ADD VALUE IF NOT EXISTS 'profit_interest'")


def downgrade() -> None:
    # Remove pension/annuity income fields
    op.drop_column('accounts', 'benefit_start_date')
    op.drop_column('accounts', 'monthly_benefit')

    # Note: PostgreSQL does not support removing enum values.
    # To fully revert, you would need to recreate the enum without 'profit_interest'.
