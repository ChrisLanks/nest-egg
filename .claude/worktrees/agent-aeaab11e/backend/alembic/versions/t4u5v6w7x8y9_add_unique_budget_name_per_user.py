"""Add unique budget name per user constraint.

Revision ID: t4u5v6w7x8y9
Revises: s3t4u5v6w7x8
Create Date: 2026-03-18

Prevent duplicate budget names for the same owner.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "t4u5v6w7x8y9"
down_revision: Union[str, None] = "s3t4u5v6w7x8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_budgets_user_name",
        "budgets",
        ["user_id", "name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_budgets_user_name", table_name="budgets")
