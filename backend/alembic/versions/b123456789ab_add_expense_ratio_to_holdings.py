"""add expense_ratio to holdings

Revision ID: b123456789ab
Revises: a679ddede7bd
Create Date: 2026-02-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b123456789ab'
down_revision = 'a679ddede7bd'
branch_labels = None
depends_on = None


def upgrade():
    # Add expense_ratio column to holdings table
    # Numeric(5, 4) allows values like 0.0003 (0.03%) to 9.9999 (999.99%)
    op.add_column('holdings', sa.Column('expense_ratio', sa.Numeric(5, 4), nullable=True))


def downgrade():
    # Remove expense_ratio column
    op.drop_column('holdings', 'expense_ratio')
