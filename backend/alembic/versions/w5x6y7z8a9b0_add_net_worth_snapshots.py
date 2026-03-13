"""Add net_worth_snapshots table for historical net worth tracking.

Revision ID: w5x6y7z8a9b0
Revises: v4w5x6y7z8a9
Create Date: 2026-03-12

Adds the net_worth_snapshots table which stores daily net worth snapshots
broken down by asset/liability category. Supports both combined household
snapshots (user_id=NULL) and per-user snapshots.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "w5x6y7z8a9b0"
down_revision: Union[str, None] = "v4w5x6y7z8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop if auto-created by SQLAlchemy model metadata
    op.execute("DROP TABLE IF EXISTS net_worth_snapshots CASCADE")
    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        # Net worth totals
        sa.Column("total_net_worth", sa.Numeric(15, 2), nullable=False),
        sa.Column("total_assets", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total_liabilities", sa.Numeric(15, 2), nullable=False, server_default="0"),
        # Asset breakdown
        sa.Column("cash_and_checking", sa.Numeric(15, 2), server_default="0"),
        sa.Column("savings", sa.Numeric(15, 2), server_default="0"),
        sa.Column("investments", sa.Numeric(15, 2), server_default="0"),
        sa.Column("retirement", sa.Numeric(15, 2), server_default="0"),
        sa.Column("property", sa.Numeric(15, 2), server_default="0"),
        sa.Column("vehicles", sa.Numeric(15, 2), server_default="0"),
        sa.Column("other_assets", sa.Numeric(15, 2), server_default="0"),
        # Liability breakdown
        sa.Column("credit_cards", sa.Numeric(15, 2), server_default="0"),
        sa.Column("loans", sa.Numeric(15, 2), server_default="0"),
        sa.Column("mortgages", sa.Numeric(15, 2), server_default="0"),
        sa.Column("student_loans", sa.Numeric(15, 2), server_default="0"),
        sa.Column("other_debts", sa.Numeric(15, 2), server_default="0"),
        # Per-account breakdown (JSONB)
        sa.Column("breakdown_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # Unique index for per-user snapshots (user_id IS NOT NULL)
    op.create_index(
        "uq_org_user_snapshot_date",
        "net_worth_snapshots",
        ["organization_id", "user_id", "snapshot_date"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    # Unique index for household snapshots (user_id IS NULL)
    op.create_index(
        "uq_org_household_snapshot_date",
        "net_worth_snapshots",
        ["organization_id", "snapshot_date"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )

    # Composite index for fast time-series queries
    op.create_index(
        "ix_net_worth_snapshots_org_user_date",
        "net_worth_snapshots",
        ["organization_id", "user_id", sa.text("snapshot_date DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_net_worth_snapshots_org_user_date", table_name="net_worth_snapshots")
    op.drop_index("uq_org_household_snapshot_date", table_name="net_worth_snapshots")
    op.drop_index("uq_org_user_snapshot_date", table_name="net_worth_snapshots")
    op.drop_table("net_worth_snapshots")
