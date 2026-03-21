"""Add tax_lots table and cost_basis_method column on accounts.

Revision ID: s1t2u3v4w5x6
Revises: r0s1t2u3v4w5
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "t3u4v5w6x7y8"
down_revision = "t2u3v4w5x6y7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop if auto-created by SQLAlchemy model metadata
    op.execute("DROP TABLE IF EXISTS tax_lots CASCADE")
    # Create tax_lots table
    op.create_table(
        "tax_lots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "holding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("holdings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("acquisition_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(15, 6), nullable=False),
        sa.Column("cost_basis_per_share", sa.Numeric(15, 4), nullable=False),
        sa.Column("total_cost_basis", sa.Numeric(15, 2), nullable=False),
        sa.Column("remaining_quantity", sa.Numeric(15, 6), nullable=False),
        sa.Column("is_closed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("sale_proceeds", sa.Numeric(15, 2), nullable=True),
        sa.Column("realized_gain_loss", sa.Numeric(15, 2), nullable=True),
        sa.Column("holding_period", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Add cost_basis_method column to accounts
    op.add_column(
        "accounts",
        sa.Column("cost_basis_method", sa.String(20), server_default="fifo", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "cost_basis_method")
    op.drop_table("tax_lots")
