"""merge_migration_heads

Revision ID: be193c0243dd
Revises: 1e002a673565, d9fcf058a622
Create Date: 2026-02-16 20:14:18.453778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be193c0243dd'
down_revision: Union[str, None] = ('1e002a673565', 'd9fcf058a622')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
