"""Add rental_type column to accounts table.

Revision ID: r68_add_rental_type
Revises: r67_add_credit_scores
Create Date: 2026-04-02

Adds rental_type enum (buy_and_hold, long_term_rental, short_term_rental)
to accounts table for rental property strategy classification.
Short-term rentals (STR) have different tax treatment and should be
surfaced differently in P&L, cash flow, and tax recommendations.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "r68_add_rental_type"
down_revision: Union[str, None] = "r67_add_credit_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type (IF NOT EXISTS not supported for CREATE TYPE in PG < 16)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE rentaltype AS ENUM ('buy_and_hold', 'long_term_rental', 'short_term_rental');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.add_column(
        "accounts",
        sa.Column("rental_type", sa.Enum("buy_and_hold", "long_term_rental", "short_term_rental", name="rentaltype"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "rental_type")
    op.execute("DROP TYPE IF EXISTS rentaltype")
