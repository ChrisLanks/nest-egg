"""add_sector_industry_to_holdings

Revision ID: 00cdb0f2deaf
Revises: 1eabc35bacee
Create Date: 2026-02-14 17:59:08.219844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00cdb0f2deaf'
down_revision: Union[str, None] = '1eabc35bacee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sector and industry columns to holdings table
    op.add_column('holdings', sa.Column('sector', sa.String(100), nullable=True))
    op.add_column('holdings', sa.Column('industry', sa.String(100), nullable=True))


def downgrade() -> None:
    # Remove sector and industry columns from holdings table
    op.drop_column('holdings', 'industry')
    op.drop_column('holdings', 'sector')
