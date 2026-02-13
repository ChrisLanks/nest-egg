"""add_user_display_name_and_monthly_start_day

Revision ID: 056d7f850487
Revises: fecf4db781a3
Create Date: 2026-02-13 03:58:05.856235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '056d7f850487'
down_revision: Union[str, None] = 'fecf4db781a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add display_name to users table
    op.add_column('users', sa.Column('display_name', sa.String(255), nullable=True))

    # Add monthly_start_day to organizations table
    op.add_column('organizations', sa.Column('monthly_start_day', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    # Remove columns
    op.drop_column('organizations', 'monthly_start_day')
    op.drop_column('users', 'display_name')
