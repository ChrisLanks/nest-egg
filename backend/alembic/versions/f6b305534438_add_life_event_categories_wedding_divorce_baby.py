"""Add wedding, divorce, new_baby life event enum categories.

Revision ID: f6b305534438
Revises: s4t5u6v7w8x9
Create Date: 2026-03-19

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6b305534438"  # pragma: allowlist secret
down_revision: Union[str, tuple, None] = "s4t5u6v7w8x9"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE lifeeventcategory ADD VALUE IF NOT EXISTS 'wedding'")
    op.execute("ALTER TYPE lifeeventcategory ADD VALUE IF NOT EXISTS 'divorce'")
    op.execute("ALTER TYPE lifeeventcategory ADD VALUE IF NOT EXISTS 'new_baby'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    pass
