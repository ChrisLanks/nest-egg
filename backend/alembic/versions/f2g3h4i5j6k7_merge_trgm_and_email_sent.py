"""merge_trgm_and_email_sent

Revision ID: f2g3h4i5j6k7
Revises: b3c4d5e6f7a8, n1o2t3i4f5y6
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2g3h4i5j6k7'
down_revision: Union[str, None] = ('b3c4d5e6f7a8', 'n1o2t3i4f5y6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
