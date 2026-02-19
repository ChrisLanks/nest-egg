"""fix_private_debt_enum_case

Revision ID: f0549612d0ad
Revises: 5bd74cf48dc5
Create Date: 2026-02-19 11:17:18.752956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0549612d0ad'
down_revision: Union[str, None] = '5bd74cf48dc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The accounttype enum was created by SQLAlchemy using enum member NAMES (uppercase).
    # The private_debt migration was added manually as lowercase 'private_debt', causing a mismatch.
    # PostgreSQL requires ALTER TYPE ADD VALUE to be committed before the value can be used,
    # so we use autocommit_block to add it outside the main transaction, then update rows.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'PRIVATE_DEBT'")

    # Now the new enum value is committed and available for use in the UPDATE.
    op.execute("UPDATE accounts SET account_type = 'PRIVATE_DEBT'::accounttype WHERE account_type::text = 'private_debt'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values, so downgrade is a no-op.
    # The 'PRIVATE_DEBT' value will remain but unused after downgrade.
    pass
