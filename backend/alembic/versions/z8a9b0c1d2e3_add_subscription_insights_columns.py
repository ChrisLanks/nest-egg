"""Add subscription insights columns to recurring_transactions.

Revision ID: z8a9b0c1d2e3
Revises: y7z8a9b0c1d2
Create Date: 2026-03-13

Feature #7: Add previous_amount, amount_change_pct, amount_change_detected_at,
and annual_cost columns for subscription price tracking and insights.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "z8a9b0c1d2e3"
down_revision: Union[str, None] = "y7z8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recurring_transactions",
        sa.Column("previous_amount", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "recurring_transactions",
        sa.Column("amount_change_pct", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "recurring_transactions",
        sa.Column("amount_change_detected_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "recurring_transactions",
        sa.Column("annual_cost", sa.Numeric(15, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recurring_transactions", "annual_cost")
    op.drop_column("recurring_transactions", "amount_change_detected_at")
    op.drop_column("recurring_transactions", "amount_change_pct")
    op.drop_column("recurring_transactions", "previous_amount")
