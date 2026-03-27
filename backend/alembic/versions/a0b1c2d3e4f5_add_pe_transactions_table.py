"""Add pe_transactions table for PE/PD capital calls and distributions.

Revision ID: a0b1c2d3e4f5
Revises: z9a8b7c6d5e4
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "z9a8b7c6d5e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type for PE transaction types
    pe_txn_type = sa.Enum("capital_call", "distribution", "nav_update", name="petransactiontype")
    pe_txn_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "pe_transactions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("transaction_type", pe_txn_type, nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("nav_after", sa.Numeric(15, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("pe_transactions")
    op.execute("DROP TYPE IF EXISTS petransactiontype")
