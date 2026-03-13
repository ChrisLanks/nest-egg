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
    # Create the enum type first
    distribution_type_enum = sa.Enum(
        "normal", "log_normal", "historical_bootstrap",
        name="distributiontype",
    )
    distribution_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "retirement_scenarios",
        sa.Column(
            "distribution_type",
            distribution_type_enum,
            nullable=False,
            server_default="normal",
        ),
    )


def downgrade() -> None:
    op.drop_column("retirement_scenarios", "distribution_type")

    # Drop the enum type
    sa.Enum(name="distributiontype").drop(op.get_bind(), checkfirst=True)
