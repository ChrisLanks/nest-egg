"""Add rental property fields to accounts.

Revision ID: a1b2c3d4e5f6
Revises: z8a9b0c1d2e3
Create Date: 2026-03-14

Add is_rental_property, rental_monthly_income, and rental_address columns
to the accounts table for rental property P&L tracking.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"  # pragma: allowlist secret
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "is_rental_property",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column("rental_monthly_income", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "accounts",
        sa.Column("rental_address", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "rental_address")
    op.drop_column("accounts", "rental_monthly_income")
    op.drop_column("accounts", "is_rental_property")
