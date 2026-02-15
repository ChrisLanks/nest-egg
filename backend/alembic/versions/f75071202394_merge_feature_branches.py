"""merge_feature_branches

Revision ID: f75071202394
Revises: 6983b851f847, e5f6g7h8i9j0
Create Date: 2026-02-15 02:55:46.415960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f75071202394'
down_revision: Union[str, None] = ('6983b851f847', 'e5f6g7h8i9j0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
