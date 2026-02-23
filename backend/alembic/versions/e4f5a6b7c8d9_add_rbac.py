"""Add RBAC tables: user_identities, permission_grants, permission_grant_audit.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-02-22

- user_identities: links app users to external IdP subjects (Cognito, Keycloak, Okta, Google)
- permission_grants: per-action per-resource delegation grants between household members
- permission_grant_audit: immutable audit log of every grant change
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # user_identities
    # ------------------------------------------------------------------
    op.create_table(
        "user_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_subject", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("provider_groups", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("linked_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])
    op.create_unique_constraint(
        "uq_user_identities_provider_subject",
        "user_identities",
        ["provider", "provider_subject"],
    )

    # ------------------------------------------------------------------
    # permission_grants
    # ------------------------------------------------------------------
    op.create_table(
        "permission_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "grantor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "grantee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actions", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "granted_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_grants_org_grantee", "permission_grants", ["organization_id", "grantee_id"])
    op.create_index("ix_grants_org_grantor", "permission_grants", ["organization_id", "grantor_id"])
    op.create_unique_constraint(
        "uq_permission_grants_unique",
        "permission_grants",
        ["grantor_id", "grantee_id", "resource_type", "resource_id"],
    )

    # ------------------------------------------------------------------
    # permission_grant_audit
    # ------------------------------------------------------------------
    op.create_table(
        "permission_grant_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "grant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("permission_grants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("grantor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("grantee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actions_before", postgresql.JSON, nullable=True),
        sa.Column("actions_after", postgresql.JSON, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_grant_audit_grant_id", "permission_grant_audit", ["grant_id"])
    op.create_index("ix_grant_audit_grantor", "permission_grant_audit", ["grantor_id"])


def downgrade() -> None:
    op.drop_index("ix_grant_audit_grantor", table_name="permission_grant_audit")
    op.drop_index("ix_grant_audit_grant_id", table_name="permission_grant_audit")
    op.drop_table("permission_grant_audit")

    op.drop_constraint("uq_permission_grants_unique", "permission_grants", type_="unique")
    op.drop_index("ix_grants_org_grantor", table_name="permission_grants")
    op.drop_index("ix_grants_org_grantee", table_name="permission_grants")
    op.drop_table("permission_grants")

    op.drop_constraint(
        "uq_user_identities_provider_subject", "user_identities", type_="unique"
    )
    op.drop_index("ix_user_identities_user_id", table_name="user_identities")
    op.drop_table("user_identities")
