"""Add transaction_attachments table.

Revision ID: s1t2u3v4w5x6
Revises: r0s1t2u3v4w5
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "u3v4w5x6y7z8"
down_revision = "t3u4v5w6x7y8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transaction_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_transaction_attachments_txn_id",
        "transaction_attachments",
        ["transaction_id"],
    )
    op.create_index(
        "ix_transaction_attachments_org_id",
        "transaction_attachments",
        ["organization_id"],
    )
    op.create_index(
        "ix_transaction_attachments_user_id",
        "transaction_attachments",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_attachments_user_id", table_name="transaction_attachments")
    op.drop_index("ix_transaction_attachments_org_id", table_name="transaction_attachments")
    op.drop_index("ix_transaction_attachments_txn_id", table_name="transaction_attachments")
    op.drop_table("transaction_attachments")
