"""Add assigned_user_id to transaction_splits for household expense splitting.

Revision ID: r76_member_split
Revises: r75_inv_access_days
Create Date: 2026-04-02

Adds `assigned_user_id` (UUID, nullable FK to users) to transaction_splits so
that each split can be attributed to a specific household member.  Supports
"split $X with partner" workflows and per-member settlement balance queries.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "r76_member_split"
down_revision: Union[str, None] = "r75_inv_access_days"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transaction_splits",
        sa.Column(
            "assigned_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_transaction_splits_assigned_user",
        "transaction_splits",
        ["assigned_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_splits_assigned_user", table_name="transaction_splits")
    op.drop_column("transaction_splits", "assigned_user_id")
