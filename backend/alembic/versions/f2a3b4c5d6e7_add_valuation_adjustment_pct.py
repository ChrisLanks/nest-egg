"""Add valuation_adjustment_pct to accounts

Percentage adjustment applied on top of auto-valuation provider estimates.
e.g., -10 for 10% discount (damage), +15 for 15% premium (upgrades).
NULL is treated as 0% (no adjustment).

Revision ID: f2a3b4c5d6e7
Revises: e4f5a6b7c8d9
Create Date: 2026-02-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = ("e4f5a6b7c8d9", "g1h2i3j4k5l6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("valuation_adjustment_pct", sa.Numeric(5, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "valuation_adjustment_pct")
