"""Add member_contributions column to savings_goals.

Revision ID: x6y7z8a9b0c1
Revises: w5x6y7z8a9b0
Create Date: 2026-03-12

Adds a JSON column to track per-member contribution amounts for shared
savings goals. Format: {user_id: amount_contributed}.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "x6y7z8a9b0c1"
down_revision: Union[str, None] = "w5x6y7z8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "savings_goals",
        sa.Column("member_contributions", postgresql.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("savings_goals", "member_contributions")
