"""Add per-category notification preferences to users.

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-03-18

Adds notification_preferences JSON column to users table.
Stores {category: bool} map; missing key means enabled.
Categories: account_syncs, account_activity, budget_alerts, milestones, household
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "u5v6w7x8y9z0"
down_revision: Union[str, None] = "t4u5v6w7x8y9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notification_preferences",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "notification_preferences")
