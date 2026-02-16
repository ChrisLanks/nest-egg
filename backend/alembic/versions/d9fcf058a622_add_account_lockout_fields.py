"""add_account_lockout_fields

Revision ID: d9fcf058a622
Revises: 4d3dec06d605
Create Date: 2026-02-16 13:57:58.044731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9fcf058a622'
down_revision: Union[str, None] = '4d3dec06d605'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add account lockout fields to users table
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove account lockout fields from users table
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
