"""merge_hsa_attachment_with_main

Revision ID: f5d3cbf4ac4d
Revises: b8c9d0e1f2a3, e3f6a5e0409f
Create Date: 2026-03-25 13:02:53.804175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5d3cbf4ac4d'
down_revision: Union[str, None] = ('b8c9d0e1f2a3', 'e3f6a5e0409f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
