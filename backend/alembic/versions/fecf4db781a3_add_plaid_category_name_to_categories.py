"""add_plaid_category_name_to_categories

Revision ID: fecf4db781a3
Revises: 7dcc04e9aba7
Create Date: 2026-02-13 02:09:18.230257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fecf4db781a3'
down_revision: Union[str, None] = '7dcc04e9aba7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add plaid_category_name column to categories table
    op.add_column('categories', sa.Column('plaid_category_name', sa.String(100), nullable=True))
    op.create_index('ix_categories_plaid_name', 'categories', ['plaid_category_name'])


def downgrade() -> None:
    # Remove plaid_category_name column from categories
    op.drop_index('ix_categories_plaid_name', 'categories')
    op.drop_column('categories', 'plaid_category_name')
