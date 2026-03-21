"""add_login_count_to_users

Revision ID: 2738daea423d
Revises: s1u2g3g4e5s6
Create Date: 2026-03-21 15:35:19.697118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2738daea423d'
down_revision: Union[str, None] = 's1u2g3g4e5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('login_count', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'login_count')
