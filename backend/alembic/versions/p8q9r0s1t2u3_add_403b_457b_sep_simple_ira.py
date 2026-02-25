"""Add 403(b), 457(b), SEP IRA, SIMPLE IRA account types.

These common US retirement account types were missing:
  - 403(b): Non-profit / education employees
  - 457(b): Government employees
  - SEP IRA: Self-employed individuals
  - SIMPLE IRA: Small business employees

Revision ID: p8q9r0s1t2u3
Revises: o7p8q9r0s1t2
Create Date: 2026-02-24 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p8q9r0s1t2u3"
down_revision: Union[str, None] = "o7p8q9r0s1t2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# New enum values to add (SQLAlchemy stores Python enum names = UPPERCASE)
NEW_VALUES = [
    "RETIREMENT_403B",
    "RETIREMENT_457B",
    "RETIREMENT_SEP_IRA",
    "RETIREMENT_SIMPLE_IRA",
]


def upgrade() -> None:
    for value in NEW_VALUES:
        # ALTER TYPE ... ADD VALUE cannot run inside a transaction block,
        # so we use autocommit_block() for each value.
        with op.get_context().autocommit_block():
            op.execute(f"ALTER TYPE accounttype ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    # A full enum rebuild would be required for a true downgrade.
    pass
