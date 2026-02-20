"""convert_recurring_frequency_to_varchar

Converts the recurring_transactions.frequency column from a native PostgreSQL
ENUM type to VARCHAR(20).  This avoids asyncpg type-codec caching issues that
cause errors when new enum values are added via ALTER TYPE without a full
connection pool restart.

Revision ID: e92a1c3f8b04
Revises: d81f3c9a2e47
Create Date: 2026-02-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e92a1c3f8b04'
down_revision: Union[str, None] = 'd81f3c9a2e47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast the native enum column to text, then rename type to VARCHAR(20).
    # The stored values ('weekly', 'biweekly', 'monthly', 'quarterly', 'yearly',
    # 'on_demand') are preserved as-is.
    op.execute(
        "ALTER TABLE recurring_transactions "
        "ALTER COLUMN frequency TYPE VARCHAR(20) USING frequency::text"
    )
    # Drop the now-unused PostgreSQL enum type.
    op.execute("DROP TYPE IF EXISTS recurringfrequency")


def downgrade() -> None:
    # Recreate the enum type and cast back (on_demand will be lost if present).
    op.execute(
        "CREATE TYPE recurringfrequency AS ENUM "
        "('weekly','biweekly','monthly','quarterly','yearly','on_demand')"
    )
    op.execute(
        "ALTER TABLE recurring_transactions "
        "ALTER COLUMN frequency TYPE recurringfrequency "
        "USING frequency::recurringfrequency"
    )
