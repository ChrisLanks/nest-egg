"""add retirement fields to user

Revision ID: c234567890bc
Revises: b123456789ab
Create Date: 2026-02-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c234567890bc'
down_revision = 'b123456789ab'
branch_labels = None
depends_on = None


def upgrade():
    # Add birthdate and target_retirement_date columns to users table
    op.add_column('users', sa.Column('birthdate', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('target_retirement_date', sa.Date(), nullable=True))


def downgrade():
    # Remove birthdate and target_retirement_date columns
    op.drop_column('users', 'target_retirement_date')
    op.drop_column('users', 'birthdate')
