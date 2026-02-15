"""add country to holdings

Revision ID: a679ddede7bd
Revises: f75071202394
Create Date: 2026-02-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a679ddede7bd'
down_revision = 'f75071202394'
branch_labels = None
depends_on = None


def upgrade():
    # Add country column to holdings table
    op.add_column('holdings', sa.Column('country', sa.String(100), nullable=True))


def downgrade():
    # Remove country column
    op.drop_column('holdings', 'country')
