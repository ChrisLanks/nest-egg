"""add excluded_account_ids to retirement_scenarios

Revision ID: df3d0a0c3995
Revises: 5b92773f35b5
Create Date: 2026-03-22

Adds excluded_account_ids (JSON text array of account UUIDs) to
retirement_scenarios. Stores which accounts the user has opted out of
a given simulation — e.g. ["<uuid1>", "<uuid2>"].
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df3d0a0c3995'
down_revision: Union[str, None] = '5b92773f35b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'retirement_scenarios',
        sa.Column('excluded_account_ids', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('retirement_scenarios', 'excluded_account_ids')
