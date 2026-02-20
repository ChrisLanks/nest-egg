"""add_on_demand_to_recurring_frequency

Revision ID: d81f3c9a2e47
Revises: c71ac9284b97
Create Date: 2026-02-20 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd81f3c9a2e47'
down_revision: Union[str, None] = 'c71ac9284b97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL native enum: add the new value
    # IF NOT EXISTS guard prevents errors if run multiple times
    op.execute("ALTER TYPE recurringfrequency ADD VALUE IF NOT EXISTS 'on_demand'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    # A full enum migration would be required; skip here.
    pass
