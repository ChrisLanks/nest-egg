"""add account lockout fields to users

Revision ID: a1b2c3d4e5f6
Revises: fecf4db781a3
Create Date: 2026-02-16 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'fecf4db781a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add account security fields to users table
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove account security fields from users table
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
