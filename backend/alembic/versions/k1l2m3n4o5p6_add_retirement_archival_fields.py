"""add_retirement_archival_fields

Revision ID: k1l2m3n4o5p6
Revises: j9k0l1m2n3o4
Create Date: 2026-03-17

Adds archival lifecycle columns to retirement_scenarios:
is_archived, archived_at, archived_reason.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "k1l2m3n4o5p6"  # pragma: allowlist secret
down_revision: Union[str, None] = "j9k0l1m2n3o4"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "retirement_scenarios",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "retirement_scenarios",
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "retirement_scenarios",
        sa.Column("archived_reason", sa.String(200), nullable=True),
    )
    op.create_index(
        "ix_retirement_archived_cleanup",
        "retirement_scenarios",
        ["is_archived", "archived_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retirement_archived_cleanup",
        table_name="retirement_scenarios",
    )
    op.drop_column("retirement_scenarios", "archived_reason")
    op.drop_column("retirement_scenarios", "archived_at")
    op.drop_column("retirement_scenarios", "is_archived")
