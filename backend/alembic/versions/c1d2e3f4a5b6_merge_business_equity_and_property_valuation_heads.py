"""merge_business_equity_and_property_valuation_heads

Revision ID: c1d2e3f4a5b6
Revises: 5bd74cf48dc5, 023448db874a
Create Date: 2026-02-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = ('5bd74cf48dc5', '023448db874a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
