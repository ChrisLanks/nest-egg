"""Add inflation_adjusted toggle and multi-currency support columns.

Revision ID: x6y7z8a9b0c1
Revises: w5x6y7z8a9b0
Create Date: 2026-03-12

Feature #3: Add inflation_adjusted boolean to retirement_scenarios so users
can toggle inflation adjustments on/off in Monte Carlo projections.

Feature #8: Add currency column to accounts and default_currency to
organizations as foundation for multi-currency support.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "x7y8z9a0b1c2"
down_revision: Union[str, None] = "x6y7z8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Feature #3: Inflation-adjusted projections toggle
    op.add_column(
        "retirement_scenarios",
        sa.Column(
            "inflation_adjusted",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )

    # Feature #8: Multi-currency support (foundation)
    op.add_column(
        "accounts",
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default="'USD'",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "default_currency",
            sa.String(3),
            nullable=False,
            server_default="'USD'",
        ),
    )


def downgrade() -> None:
    op.drop_column("organizations", "default_currency")
    op.drop_column("accounts", "currency")
    op.drop_column("retirement_scenarios", "inflation_adjusted")
