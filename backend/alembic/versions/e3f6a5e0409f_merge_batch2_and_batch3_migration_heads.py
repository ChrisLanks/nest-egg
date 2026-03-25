"""merge batch2 and batch3 migration heads

Revision ID: e3f6a5e0409f
Revises: f6a7b8c9d0e2, q2r3s4t5u6v7
Create Date: 2026-03-25 00:27:24.861053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f6a5e0409f'
down_revision: Union[str, None] = ('f6a7b8c9d0e2', 'q2r3s4t5u6v7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
