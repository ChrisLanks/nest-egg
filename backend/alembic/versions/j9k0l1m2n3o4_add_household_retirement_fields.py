"""add_household_retirement_fields

Revision ID: j9k0l1m2n3o4
Revises: i9j0k1l2m3n4
Create Date: 2026-03-17

Adds household-wide retirement planning columns to retirement_scenarios:
include_all_members, household_member_hash, household_member_ids.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "j9k0l1m2n3o4"  # pragma: allowlist secret
down_revision: Union[str, None] = "i9j0k1l2m3n4"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "retirement_scenarios",
        sa.Column("include_all_members", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "retirement_scenarios",
        sa.Column("household_member_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "retirement_scenarios",
        sa.Column("household_member_ids", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("retirement_scenarios", "household_member_ids")
    op.drop_column("retirement_scenarios", "household_member_hash")
    op.drop_column("retirement_scenarios", "include_all_members")
