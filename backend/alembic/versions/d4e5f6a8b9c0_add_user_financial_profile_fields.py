"""add user financial profile fields

Revision ID: d4e5f6a8b9c0
Revises: c3d4e5f6a8b9
Create Date: 2026-03-24 00:00:00.000000

Adds paycheck frequency, income type, self-employment flag, state of
residence, target retirement state, and minimum monthly budget to users.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a8b9c0'
down_revision: Union[str, None] = 'c3d4e5f6a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('paycheck_frequency', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('next_paycheck_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('income_type', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('is_self_employed', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('state_of_residence', sa.String(2), nullable=True))
    op.add_column('users', sa.Column('target_retirement_state', sa.String(2), nullable=True))
    op.add_column('users', sa.Column('minimum_monthly_budget', sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'minimum_monthly_budget')
    op.drop_column('users', 'target_retirement_state')
    op.drop_column('users', 'state_of_residence')
    op.drop_column('users', 'is_self_employed')
    op.drop_column('users', 'income_type')
    op.drop_column('users', 'next_paycheck_date')
    op.drop_column('users', 'paycheck_frequency')
