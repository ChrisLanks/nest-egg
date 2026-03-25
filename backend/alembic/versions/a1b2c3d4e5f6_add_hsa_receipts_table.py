"""Add hsa_receipts table.

Revision ID: a1b2c3d4e5f6
Revises: z8a9b0c1d2e3
Create Date: 2026-03-24

Feature #2: Add hsa_receipts table for HSA expense tracking and optimization.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "z8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hsa_receipts CASCADE")
    op.create_table(
        "hsa_receipts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column(
            "is_reimbursed", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("reimbursed_at", sa.Date(), nullable=True),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_hsa_receipts_org_user",
        "hsa_receipts",
        ["organization_id", "user_id"],
    )
    op.create_index(
        "ix_hsa_receipts_tax_year",
        "hsa_receipts",
        ["tax_year"],
    )


def downgrade() -> None:
    op.drop_index("ix_hsa_receipts_tax_year", table_name="hsa_receipts")
    op.drop_index("ix_hsa_receipts_org_user", table_name="hsa_receipts")
    op.drop_table("hsa_receipts")
