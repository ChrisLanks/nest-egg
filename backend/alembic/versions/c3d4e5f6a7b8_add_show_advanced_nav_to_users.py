"""Add show_advanced_nav column to users table.

Revision ID: r65_add_show_advanced_nav
Revises: r62a1b2c3d4e5, r64_add_gift_records
Create Date: 2026-04-02

"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "r65_add_show_advanced_nav"
down_revision: Union[str, tuple] = ("r62a1b2c3d4e5", "r64_add_gift_records")
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
