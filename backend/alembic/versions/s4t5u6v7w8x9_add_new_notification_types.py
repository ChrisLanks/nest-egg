"""Add weekly_recap, equity_vesting, crypto_price_alert notification types.

Revision ID: s4t5u6v7w8x9
Revises: b2c3d4e5f6a7, c3d4e5f6a7b8, h8i9j0k1l2m3, i9j0k1l2m3n4, k1l2m3n4o5p6, u5v6w7x8y9z0
Create Date: 2026-03-19

Merges outstanding heads and adds three new notification enum values.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "s4t5u6v7w8x9"
down_revision: Union[str, tuple, None] = (  # pragma: allowlist secret
    "b2c3d4e5f6a7",  # pragma: allowlist secret
    "c3d4e5f6a7b8",  # pragma: allowlist secret
    "h8i9j0k1l2m3",  # pragma: allowlist secret
    "i9j0k1l2m3n4",
    "k1l2m3n4o5p6",  # pragma: allowlist secret
    "u5v6w7x8y9z0",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'weekly_recap'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'equity_vesting'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'crypto_price_alert'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    # The extra values are harmless if this migration is rolled back.
    pass
