"""Add semi_annual budget period.

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-03-17

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE budgetperiod ADD VALUE IF NOT EXISTS 'semi_annual'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly.
    pass
