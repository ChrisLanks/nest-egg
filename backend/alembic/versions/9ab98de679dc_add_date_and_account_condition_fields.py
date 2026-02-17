"""add_date_and_account_condition_fields

Revision ID: 9ab98de679dc
Revises: be193c0243dd
Create Date: 2026-02-16 20:14:20.978386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ab98de679dc'
down_revision: Union[str, None] = 'be193c0243dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values to conditionfield enum type
    # PostgreSQL requires ALTER TYPE ... ADD VALUE for enum additions
    op.execute("ALTER TYPE conditionfield ADD VALUE IF NOT EXISTS 'date'")
    op.execute("ALTER TYPE conditionfield ADD VALUE IF NOT EXISTS 'month'")
    op.execute("ALTER TYPE conditionfield ADD VALUE IF NOT EXISTS 'year'")
    op.execute("ALTER TYPE conditionfield ADD VALUE IF NOT EXISTS 'day_of_week'")
    op.execute("ALTER TYPE conditionfield ADD VALUE IF NOT EXISTS 'account_id'")
    op.execute("ALTER TYPE conditionfield ADD VALUE IF NOT EXISTS 'account_type'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # You would need to recreate the enum type to remove values
    # For safety, we'll leave the enum values in place on downgrade
    pass
