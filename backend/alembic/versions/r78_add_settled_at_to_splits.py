"""Add settled_at to transaction_splits for household settlement tracking.

Revision ID: r78_add_settled_at
Revises: r77_household_notif
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa

revision = "r78_add_settled_at"
down_revision = "r77_household_notif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transaction_splits",
        sa.Column("settled_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transaction_splits", "settled_at")
