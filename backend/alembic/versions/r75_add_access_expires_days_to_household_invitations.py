"""Add access_expires_days column to household_invitations table.

Revision ID: r75_add_access_expires_days_invitations
Revises: 6026601bc27e
Create Date: 2026-04-02

The HouseholdInvitation model declares access_expires_days (Integer, nullable)
to support guest invitations that auto-expire after a set number of days.
The column was previously added only to household_guest_invitations; this
migration adds it to the household_invitations table where the model expects it.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "r75_inv_access_days"
down_revision: Union[str, None] = "6026601bc27e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "household_invitations",
        sa.Column("access_expires_days", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("household_invitations", "access_expires_days")
