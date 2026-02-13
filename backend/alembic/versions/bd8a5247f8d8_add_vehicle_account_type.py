"""add_missing_account_types

Revision ID: bd8a5247f8d8
Revises: abc123def456
Create Date: 2026-02-13 07:22:16.023766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd8a5247f8d8'
down_revision: Union[str, None] = 'abc123def456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing account types to the accounttype enum (uppercase to match existing values)
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'VEHICLE'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'PROPERTY'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'LOAN'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'MORTGAGE'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'CRYPTO'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # This would require recreating the enum, which is complex
    # For now, we'll leave the value in the database
    pass
