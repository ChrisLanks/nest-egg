"""merge_all_heads

Revision ID: p1m2a3u4d5i6
Revises: m1s2c3o4l5m6, f2g3h4i5j6k7
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'p1m2a3u4d5i6'
down_revision: Union[str, None] = ('m1s2c3o4l5m6', 'f2g3h4i5j6k7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
