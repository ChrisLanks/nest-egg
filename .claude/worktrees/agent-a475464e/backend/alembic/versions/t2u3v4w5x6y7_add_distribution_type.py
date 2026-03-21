"""Add distribution_type column to retirement_scenarios.

Revision ID: t2u3v4w5x6y7
Revises: r0s1t2u3v4w5
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "t2u3v4w5x6y7"
down_revision = "r0s1t2u3v4w5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the enum type first (raw SQL for async compatibility)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE distributiontype AS ENUM "
        "('NORMAL', 'LOG_NORMAL', 'HISTORICAL_BOOTSTRAP'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    op.add_column(
        "retirement_scenarios",
        sa.Column(
            "distribution_type",
            sa.Enum(
                "NORMAL", "LOG_NORMAL", "HISTORICAL_BOOTSTRAP",
                name="distributiontype",
                create_type=False,
            ),
            nullable=False,
            server_default="NORMAL",
        ),
    )


def downgrade() -> None:
    op.drop_column("retirement_scenarios", "distribution_type")
    op.execute("DROP TYPE IF EXISTS distributiontype")
