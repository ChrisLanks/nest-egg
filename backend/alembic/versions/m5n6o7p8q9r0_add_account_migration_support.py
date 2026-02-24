"""Add account migration support: migration log table + previous_external_account_id column.

Revision ID: m5n6o7p8q9r0
Revises: l4m5n6o7p8q9
Create Date: 2026-02-24 21:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "m5n6o7p8q9r0"
down_revision: Union[str, None] = "l4m5n6o7p8q9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add previous_external_account_id to accounts
    op.add_column(
        "accounts",
        sa.Column("previous_external_account_id", sa.String(255), nullable=True),
    )

    # 2. Create migration log table
    op.create_table(
        "account_migration_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "initiated_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_provider", sa.String(20), nullable=False),
        sa.Column("target_provider", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("pre_migration_snapshot", sa.JSON(), nullable=False),
        sa.Column("post_migration_snapshot", sa.JSON(), nullable=True),
        sa.Column("target_enrollment_id", UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("initiated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    # 3. Create indexes
    op.create_index(
        "ix_migration_log_account",
        "account_migration_logs",
        ["account_id"],
    )
    op.create_index(
        "ix_migration_log_org_date",
        "account_migration_logs",
        ["organization_id", "initiated_at"],
    )
    op.create_index(
        "ix_migration_log_org_id",
        "account_migration_logs",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_table("account_migration_logs")
    op.drop_column("accounts", "previous_external_account_id")
