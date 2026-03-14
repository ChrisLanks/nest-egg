"""Add milestone and all_time_high notification types.

Revision ID: a9b0c1d2e3f4
Revises: z8a9b0c1d2e3
Create Date: 2026-03-14

Add MILESTONE and ALL_TIME_HIGH values to the notificationtype enum
for net worth milestone detection and all-time-high notifications.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"  # pragma: allowlist secret
down_revision: Union[str, None] = "539b8bbbf1c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'MILESTONE'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'ALL_TIME_HIGH'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # The extra values are harmless if the feature is rolled back.
    pass
