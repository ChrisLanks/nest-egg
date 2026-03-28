"""Fix notificationtype enum case: add lowercase fire_coast_fi and fire_independent.

Revision ID: r65_fix_notification_enum_case
Revises: r64_add_gift_records
Create Date: 2026-03-28

The r2s3t4u5v6w7 migration added FIRE_COAST_FI and FIRE_INDEPENDENT (uppercase)
but the Python NotificationType enum uses lowercase values. PostgreSQL enum values
are case-sensitive, so SQLAlchemy inserts fail with InvalidTextRepresentationError.
This migration adds the lowercase variants.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r65_fix_notification_enum_case"
down_revision: Union[str, None] = "r64_add_gift_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # r2s3t4u5v6w7 added these uppercase; Python enum expects lowercase
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'account_connected'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'household_member_joined'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'household_member_left'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'fire_coast_fi'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'fire_independent'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'retirement_scenario_stale'")
    # b2c3d4e5f6a7 added these uppercase; Python enum expects lowercase
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'milestone'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'all_time_high'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    pass
