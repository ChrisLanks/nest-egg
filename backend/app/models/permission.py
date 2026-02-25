"""RBAC permission grant models."""

import uuid
from typing import Final

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda

# ---------------------------------------------------------------------------
# Constants — keep in sync with frontend ResourceType type
# ---------------------------------------------------------------------------

RESOURCE_TYPES: Final[tuple] = (
    "account",
    "transaction",
    "bill",
    "holding",
    "budget",
    "category",
    "rule",
    "savings_goal",
    "contribution",
    "recurring_transaction",
    "report",
    "org_settings",
    "retirement_scenario",
)

GRANT_ACTIONS: Final[tuple] = ("read", "create", "update", "delete")


class PermissionGrant(Base):
    """Delegation grant: the owner (grantor) gives another user (grantee) access
    to a specific resource type or resource instance.

    Examples::

        # Alice grants Bob read+create access to ALL of Alice's transactions
        grantor=alice, grantee=bob, resource_type="transaction",
        resource_id=None, actions=["read","create"]

        # Alice grants Bob read access to one specific account
        grantor=alice, grantee=bob, resource_type="account",
        resource_id=<account_uuid>, actions=["read"]

    The ``grant`` permission (resource_type="permission") is intentionally
    never grantable via this table — only org admins and resource owners may
    manage grants directly.
    """

    __tablename__ = "permission_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The user whose data is being shared
    grantor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The user receiving delegated access
    grantee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Resource type (see RESOURCE_TYPES above)
    resource_type = Column(String(50), nullable=False)
    # Specific resource UUID; NULL means all resources of this type owned by grantor
    resource_id = Column(UUID(as_uuid=True), nullable=True)

    # JSON array of strings, e.g. ["read", "update"]
    actions = Column(JSON, nullable=False, default=list)

    granted_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Who created the grant (usually == grantor_id; could be org admin)
    granted_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    grantor = relationship("User", foreign_keys=[grantor_id])
    grantee = relationship("User", foreign_keys=[grantee_id])
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        # Prevent duplicate grants for the same (grantor, grantee, resource)
        UniqueConstraint(
            "grantor_id",
            "grantee_id",
            "resource_type",
            "resource_id",
            name="uq_permission_grants_unique",
        ),
        # Fast lookup: "what can I (grantee) access in this org?"
        Index("ix_grants_org_grantee", "organization_id", "grantee_id"),
        # Fast lookup: "what have I (grantor) shared in this org?"
        Index("ix_grants_org_grantor", "organization_id", "grantor_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<PermissionGrant {self.grantor_id!s}→{self.grantee_id!s}"
            f" {self.resource_type} {self.actions}>"
        )


class PermissionGrantAudit(Base):
    """Immutable audit log for every permission grant event.

    Rows are never updated or deleted. Grant IDs are kept even after the parent
    grant is revoked (is_active=False) or physically deleted, so the history
    is always complete. Grantor/grantee IDs are denormalized for the same reason.
    """

    __tablename__ = "permission_grant_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Nullable: FK survives grant deletion (via SET NULL), so history is preserved
    grant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("permission_grants.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 'created', 'updated', 'revoked'
    action = Column(String(50), nullable=False)

    # Who made this change
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Denormalized so the audit survives grant + user deletion
    grantor_id = Column(UUID(as_uuid=True), nullable=True)
    grantee_id = Column(UUID(as_uuid=True), nullable=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)

    # JSON arrays: None on create; None on revoke
    actions_before = Column(JSON, nullable=True)
    actions_after = Column(JSON, nullable=True)

    ip_address = Column(String(45), nullable=True)
    occurred_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    __table_args__ = (
        Index("ix_grant_audit_grant_id", "grant_id"),
        Index("ix_grant_audit_grantor", "grantor_id"),
    )

    def __repr__(self) -> str:
        return f"<PermissionGrantAudit {self.action!r} grant={self.grant_id!s}>"
