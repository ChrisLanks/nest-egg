"""Add onboarding_goal column to users table.

Revision ID: a1b2c3d4e5f8
Revises: 2738daea423d
Create Date: 2026-03-21

Stores the goal the user selected during the onboarding wizard so it can
be read back when localStorage is unavailable (e.g. different device,
cleared storage).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f8"
down_revision: Union[str, None] = "2738daea423d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_goal", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_goal")
