"""merge_all_heads_r70

Revision ID: 6026601bc27e
Revises: b2c3d4e5f7a8, r65_add_show_advanced_nav, r69_add_lp_interest
Create Date: 2026-04-02 21:08:13.172854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6026601bc27e'
down_revision: Union[str, None] = ('b2c3d4e5f7a8', 'r65_add_show_advanced_nav', 'r69_add_lp_interest')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
