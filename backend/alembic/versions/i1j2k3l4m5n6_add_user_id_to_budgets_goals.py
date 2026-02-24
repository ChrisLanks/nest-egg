"""Add user_id to budgets and savings_goals for ownership tracking.

Revision ID: i1j2k3l4m5n6
Revises: h1i2j3k4l5m6
Create Date: 2026-02-24 14:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "i1j2k3l4m5n6"
down_revision: Union[str, None] = "h1i2j3k4l5m6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id to budgets (nullable initially for existing rows)
    op.add_column("budgets", sa.Column("user_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_budgets_user_id",
        "budgets",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])

    # Add user_id to savings_goals (nullable initially for existing rows)
    op.add_column("savings_goals", sa.Column("user_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_savings_goals_user_id",
        "savings_goals",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_savings_goals_user_id", table_name="savings_goals")
    op.drop_constraint("fk_savings_goals_user_id", "savings_goals", type_="foreignkey")
    op.drop_column("savings_goals", "user_id")

    op.drop_index("ix_budgets_user_id", table_name="budgets")
    op.drop_constraint("fk_budgets_user_id", "budgets", type_="foreignkey")
    op.drop_column("budgets", "user_id")
