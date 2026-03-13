"""Add bulk_operation_logs table and onboarding columns to users.

Revision ID: y7z8a9b0c1d2
Revises: x6y7z8a9b0c1
Create Date: 2026-03-12

Feature #18: Add bulk_operation_logs table for undo/redo support on bulk
operations (categorize, merge, delete, split).

Feature #20: Add onboarding_completed and onboarding_step columns to users
table for onboarding wizard state tracking.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "y7z8a9b0c1d2"
down_revision: Union[str, None] = "x7y8z9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Feature #18: Bulk operation logs ---
    # Drop if auto-created by SQLAlchemy model metadata
    op.execute("DROP TABLE IF EXISTS bulk_operation_logs CASCADE")
    op.create_table(
        "bulk_operation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
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
        sa.Column("operation_type", sa.String(50), nullable=False),
        sa.Column("affected_ids", sa.JSON(), nullable=False),
        sa.Column("previous_state", sa.JSON(), nullable=False),
        sa.Column("new_state", sa.JSON(), nullable=True),
        sa.Column("is_undone", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("undone_at", sa.DateTime(), nullable=True),
    )

    # Indexes for common queries
    op.create_index(
        "ix_bulk_operation_logs_org_user",
        "bulk_operation_logs",
        ["organization_id", "user_id"],
    )
    op.create_index(
        "ix_bulk_operation_logs_created_at",
        "bulk_operation_logs",
        ["created_at"],
    )

    # --- Feature #20: Onboarding columns on users ---
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column("onboarding_step", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    # --- Feature #20 ---
    op.drop_column("users", "onboarding_step")
    op.drop_column("users", "onboarding_completed")

    # --- Feature #18 ---
    op.drop_index("ix_bulk_operation_logs_created_at", table_name="bulk_operation_logs")
    op.drop_index("ix_bulk_operation_logs_org_user", table_name="bulk_operation_logs")
    op.drop_table("bulk_operation_logs")
