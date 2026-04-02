"""Add show_advanced_nav column to users table.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f7a8
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "show_advanced_nav",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "show_advanced_nav")
