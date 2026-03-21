"""Add transaction notes and flagged_for_review fields.

Revision ID: a9b0c1d2e3f4
Revises: z8a9b0c1d2e3
Create Date: 2026-03-14

Adds notes (free-form text) and flagged_for_review (boolean) columns
to the transactions table for user annotations and household review.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"  # pragma: allowlist secret
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "transactions",
        sa.Column("flagged_for_review", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "ix_transactions_org_flagged_date",
        "transactions",
        ["organization_id", "flagged_for_review", "date"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_org_flagged_date", table_name="transactions")
    op.drop_column("transactions", "flagged_for_review")
    op.drop_column("transactions", "notes")
