"""Merge r62 branch and r65 branch into single head.

Revision ID: r66_merge_heads
Revises: r62a1b2c3d4e5, r65_fix_notification_enum_case
Create Date: 2026-03-28
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "r66_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "r62a1b2c3d4e5",
    "r65_fix_notification_enum_case",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
