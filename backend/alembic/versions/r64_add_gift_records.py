"""Add gift_records table.

Revision ID: r64_add_gift_records
Revises: a0b1c2d3e4f5
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "r64_add_gift_records"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='gift_records')")
    ).scalar()
    if exists:
        return

    op.create_table(
        "gift_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "donor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("year", sa.Integer, nullable=False, index=True),
        sa.Column("recipient_name", sa.String(200), nullable=False),
        sa.Column("recipient_relationship", sa.String(100), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("is_529_superfunding", sa.Boolean, default=False, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("gift_records")
