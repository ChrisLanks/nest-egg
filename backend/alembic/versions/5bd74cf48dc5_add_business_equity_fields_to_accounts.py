"""add_business_equity_fields_to_accounts

Revision ID: 5bd74cf48dc5
Revises: 5127a6d0b6d1
Create Date: 2026-02-18 23:55:54.538479

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bd74cf48dc5'
down_revision: Union[str, None] = '5127a6d0b6d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add business equity fields
    op.add_column('accounts', sa.Column('company_valuation', sa.Numeric(15, 2), nullable=True))
    op.add_column('accounts', sa.Column('ownership_percentage', sa.Numeric(5, 2), nullable=True))
    op.add_column('accounts', sa.Column('equity_value', sa.Numeric(15, 2), nullable=True))


def downgrade() -> None:
    # Remove business equity fields
    op.drop_column('accounts', 'equity_value')
    op.drop_column('accounts', 'ownership_percentage')
    op.drop_column('accounts', 'company_valuation')
