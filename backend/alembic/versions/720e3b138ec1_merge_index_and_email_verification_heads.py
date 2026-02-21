"""merge_index_and_email_verification_heads

Revision ID: 720e3b138ec1
Revises: a2b3c4d5e6f7, f7a8b2c1d9e3
Create Date: 2026-02-20 21:56:32.207714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '720e3b138ec1'
down_revision: Union[str, None] = ('a2b3c4d5e6f7', 'f7a8b2c1d9e3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
