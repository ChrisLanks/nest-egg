"""add_spending_phases

Revision ID: q1r2s3t4u5v6
Revises: k1l2m3n4o5p6
Create Date: 2026-03-17

Adds spending_phases column to retirement_scenarios for variable
spending across retirement (JSON array of phase objects).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "q1r2s3t4u5v6"
down_revision: Union[str, None] = "k1l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "retirement_scenarios",
        sa.Column("spending_phases", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("retirement_scenarios", "spending_phases")
