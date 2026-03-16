"""Add household guest access tables.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-15

Adds household_guests and household_guest_invitations tables
for cross-household guest viewing without merging data.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"  # pragma: allowlist secret
down_revision: Union[str, None] = "e5f6a7b8c9d0"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create guest_role enum
    guest_role = sa.Enum("viewer", "advisor", name="guest_role")
    guest_role.create(op.get_bind(), checkfirst=True)

    # Create guest_invitation_status enum
    guest_inv_status = sa.Enum("pending", "accepted", "declined", "expired", name="guest_invitation_status")
    guest_inv_status.create(op.get_bind(), checkfirst=True)

    # household_guests table
    op.create_table(
        "household_guests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "invited_by_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("role", guest_role, nullable=False, server_default="viewer"),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "revoked_by_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_guest_user_org"),
    )

    # household_guest_invitations table
    op.create_table(
        "household_guest_invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "invited_by_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("invitation_code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("role", guest_role, nullable=False, server_default="viewer"),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("status", guest_inv_status, nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("household_guest_invitations")
    op.drop_table("household_guests")

    sa.Enum(name="guest_invitation_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="guest_role").drop(op.get_bind(), checkfirst=True)
