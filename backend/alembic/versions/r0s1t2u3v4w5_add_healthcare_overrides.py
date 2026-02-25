"""Add healthcare cost override columns to retirement_scenarios.

Revision ID: r0s1t2u3v4w5
Revises: q9r0s1t2u3v4
Create Date: 2026-02-24

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "r0s1t2u3v4w5"
down_revision = "q9r0s1t2u3v4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "retirement_scenarios",
        sa.Column("healthcare_pre65_override", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "retirement_scenarios",
        sa.Column("healthcare_medicare_override", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "retirement_scenarios",
        sa.Column("healthcare_ltc_override", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("retirement_scenarios", "healthcare_ltc_override")
    op.drop_column("retirement_scenarios", "healthcare_medicare_override")
    op.drop_column("retirement_scenarios", "healthcare_pre65_override")
