"""Add missing AccountType enum values to PostgreSQL

Revision ID: a1b2c3d4e5f6
Revises: z9a8b7c6d5e4
Create Date: 2026-03-26

Adds enum labels that exist in the Python AccountType enum but were never
migrated to the DB: I_BOND, TIPS, TRUST, CUSTODIAL_UGMA, TRUMP_ACCOUNT.

PostgreSQL requires ALTER TYPE ... ADD VALUE for enum additions.
Each ADD VALUE is run in its own implicit transaction (cannot run inside
an explicit BEGIN/COMMIT block with asyncpg).
"""

from alembic import op

# revision identifiers
revision = "37e1d1767687"
down_revision = "z9a8b7c6d5e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADD VALUE IF NOT EXISTS is safe to re-run
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'I_BOND'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'TIPS'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'TRUST'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'CUSTODIAL_UGMA'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'TRUMP_ACCOUNT'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op.
    pass
