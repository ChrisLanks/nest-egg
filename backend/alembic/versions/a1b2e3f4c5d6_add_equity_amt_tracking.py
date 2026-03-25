"""add equity AMT tracking

Revision ID: a1b2e3f4c5d6
Revises: 3f8a1b2c9d4e
Create Date: 2026-03-24 00:00:00.000000

Adds iso_exercise_basis to accounts for cumulative ISO exercised AMT tracking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2e3f4c5d6'
down_revision: Union[str, None] = '3f8a1b2c9d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('iso_exercise_basis', sa.Numeric(15, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'iso_exercise_basis')
