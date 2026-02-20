"""add_dashboard_layout_to_users

Revision ID: fe399652318d
Revises: f65f5ac15458
Create Date: 2026-02-20 02:38:21.670199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe399652318d'
down_revision: Union[str, None] = 'f65f5ac15458'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('dashboard_layout', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'dashboard_layout')
