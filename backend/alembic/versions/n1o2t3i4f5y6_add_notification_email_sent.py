"""Add email_sent column to notifications for delivery tracking

Revision ID: n1o2t3i4f5y6
Revises: z8a9b0c1d2e3
Create Date: 2026-03-21

Adds a nullable boolean column `email_sent` to the notifications table.
- NULL  = no email was attempted (in-app notification only)
- True  = email was sent successfully
- False = email send was attempted but failed

This gives an audit trail for delivery failures instead of silent drops.
"""

from alembic import op
import sqlalchemy as sa

revision = "n1o2t3i4f5y6"
down_revision = "z8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("email_sent", sa.Boolean(), nullable=True, server_default=None),
    )


def downgrade() -> None:
    op.drop_column("notifications", "email_sent")
