"""Add trump_account type to accounttype enum

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-03-16

Adds trump_account (custodial traditional IRA for minors under OBBBA)
to the accounttype enum.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "h8i9j0k1l2m3"  # pragma: allowlist secret
down_revision: Union[str, None] = "g7h8i9j0k1l2"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'trump_account'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly
    pass
