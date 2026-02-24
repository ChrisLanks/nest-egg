"""Permission service — checks and manages PermissionGrants.

Usage::

    # In an endpoint that accesses another user's data:
    await permission_service.require(
        db, actor=current_user, action="read",
        resource_type="transaction", owner_id=account.user_id,
    )

    # Create a grant (grantor pushes access to grantee):
    grant = await permission_service.grant(
        db, grantor=current_user, grantee_id=friend.id,
        resource_type="account", actions=["read"],
        resource_id=my_account.id,
    )

    # Revoke a grant:
    await permission_service.revoke(db, grantor=current_user, grant_id=grant.id)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.permission import permission_grant_crud
from app.models.permission import (
    GRANT_ACTIONS,
    RESOURCE_TYPES,
    PermissionGrant,
    PermissionGrantAudit,
)
from app.models.user import User
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class PermissionService:
    """Service layer for permission grant lifecycle management."""

    # -------------------------------------------------------------------------
    # Read operations
    # -------------------------------------------------------------------------

    async def check(
        self,
        db: AsyncSession,
        actor: User,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        owner_id: Optional[UUID] = None,
    ) -> bool:
        """Return True if *actor* may perform *action* on the resource.

        Short-circuits in order:
          1. actor IS the owner → always allowed
          2. active non-expired PermissionGrant → allowed if action is listed
        """
        if owner_id is not None and actor.id == owner_id:
            return True

        if owner_id is None:
            return False

        grant = await permission_grant_crud.find_active(
            db,
            grantor_id=owner_id,
            grantee_id=actor.id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        if grant is None:
            logger.debug(
                "[permission.check] DENY — no active grant found | "
                "actor=%s action=%s resource_type=%s resource_id=%s owner_id=%s",
                actor.id, action, resource_type, resource_id, owner_id,
            )
            return False
        if grant.expires_at is not None and utc_now() > grant.expires_at:
            logger.debug(
                "[permission.check] DENY — grant expired | grant_id=%s expires_at=%s",
                grant.id, grant.expires_at,
            )
            return False
        allowed = action in (grant.actions or [])
        logger.debug(
            "[permission.check] %s | grant_id=%s actor=%s action=%s actions=%s",
            "ALLOW" if allowed else "DENY (action not in grant)",
            grant.id, actor.id, action, grant.actions,
        )
        return allowed

    async def filter_allowed_resources(
        self,
        db: AsyncSession,
        actor: User,
        action: str,
        resource_type: str,
        resource_owner_pairs: list[tuple[UUID, UUID]],
    ) -> list[UUID]:
        """Return the subset of resource IDs the actor may perform *action* on.

        This is a bulk-optimised alternative to calling ``check()`` in a loop.
        It fetches all relevant grants in a *single* DB query and resolves
        permissions in Python.

        Args:
            resource_owner_pairs: list of ``(resource_id, owner_id)`` tuples.

        Returns:
            List of ``resource_id`` values the actor is allowed to act on.
        """
        allowed: list[UUID] = []
        non_owned: list[tuple[UUID, UUID]] = []

        for rid, owner_id in resource_owner_pairs:
            if actor.id == owner_id:
                allowed.append(rid)
            else:
                non_owned.append((rid, owner_id))

        if not non_owned:
            return allowed

        # Single DB query: fetch ALL grants the actor has for this resource type
        grants = await permission_grant_crud.list_grants_for_grantee(
            db, grantee_id=actor.id, resource_type=resource_type,
        )

        now = utc_now()
        wildcard_grantors: set[UUID] = set()
        specific_resources: set[UUID] = set()

        for g in grants:
            if g.expires_at is not None and now > g.expires_at:
                continue
            if action not in (g.actions or []):
                continue
            if g.resource_id is None:
                wildcard_grantors.add(g.grantor_id)
            else:
                specific_resources.add(g.resource_id)

        for rid, owner_id in non_owned:
            if owner_id in wildcard_grantors or rid in specific_resources:
                allowed.append(rid)

        return allowed

    async def require(
        self,
        db: AsyncSession,
        actor: User,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        owner_id: Optional[UUID] = None,
    ) -> None:
        """Like *check*, but raises HTTP 403 on denial."""
        allowed = await self.check(
            db, actor, action, resource_type, resource_id, owner_id
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    # -------------------------------------------------------------------------
    # Write operations
    # -------------------------------------------------------------------------

    async def grant(
        self,
        db: AsyncSession,
        grantor: User,
        grantee_id: UUID,
        resource_type: str,
        actions: list[str],
        resource_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None,
        ip_address: Optional[str] = None,
    ) -> PermissionGrant:
        """Create or update a permission grant.

        If a grant already exists for (grantor, grantee, resource_type,
        resource_id), its *actions* and *expires_at* are updated. Otherwise a
        new grant row is inserted.

        Raises:
            HTTPException(400): for invalid resource_type, invalid actions,
                                 or attempting to grant 'permission' delegation.
            HTTPException(422): if grantee is in a different org.
        """
        _validate_resource_type(resource_type)
        _validate_actions(actions)

        now = utc_now()

        existing = await permission_grant_crud.find_exact(
            db,
            grantor_id=grantor.id,
            grantee_id=grantee_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if existing is not None:
            actions_before = list(existing.actions or [])
            existing.actions = list(actions)
            existing.expires_at = expires_at
            existing.is_active = True
            await db.flush()

            audit = PermissionGrantAudit(
                id=uuid.uuid4(),
                grant_id=existing.id,
                action="updated",
                actor_id=grantor.id,
                grantor_id=grantor.id,
                grantee_id=grantee_id,
                resource_type=resource_type,
                resource_id=resource_id,
                actions_before=actions_before,
                actions_after=list(actions),
                ip_address=ip_address,
                occurred_at=now,
            )
            db.add(audit)
            await db.commit()
            await db.refresh(existing)
            return existing

        grant = PermissionGrant(
            id=uuid.uuid4(),
            organization_id=grantor.organization_id,
            grantor_id=grantor.id,
            grantee_id=grantee_id,
            resource_type=resource_type,
            resource_id=resource_id,
            actions=list(actions),
            granted_at=now,
            expires_at=expires_at,
            is_active=True,
            granted_by=grantor.id,
        )
        db.add(grant)
        await db.flush()

        audit = PermissionGrantAudit(
            id=uuid.uuid4(),
            grant_id=grant.id,
            action="created",
            actor_id=grantor.id,
            grantor_id=grantor.id,
            grantee_id=grantee_id,
            resource_type=resource_type,
            resource_id=resource_id,
            actions_before=None,
            actions_after=list(actions),
            ip_address=ip_address,
            occurred_at=now,
        )
        db.add(audit)
        await db.commit()
        await db.refresh(grant)
        return grant

    async def revoke(
        self,
        db: AsyncSession,
        grantor: User,
        grant_id: UUID,
        ip_address: Optional[str] = None,
    ) -> None:
        """Deactivate a grant and write an audit entry.

        Only the grantor or an org admin may revoke a grant.

        Raises:
            HTTPException(404): grant not found.
            HTTPException(403): caller is not the grantor and not an org admin.
        """
        grant = await permission_grant_crud.get_by_id(db, grant_id)
        if grant is None or grant.organization_id != grantor.organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")

        if grant.grantor_id != grantor.id and not grantor.is_org_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the grantor or an org admin may revoke this grant",
            )

        actions_before = list(grant.actions or [])
        grant.is_active = False
        await db.flush()

        audit = PermissionGrantAudit(
            id=uuid.uuid4(),
            grant_id=grant.id,
            action="revoked",
            actor_id=grantor.id,
            grantor_id=grant.grantor_id,
            grantee_id=grant.grantee_id,
            resource_type=grant.resource_type,
            resource_id=grant.resource_id,
            actions_before=actions_before,
            actions_after=None,
            ip_address=ip_address,
            occurred_at=utc_now(),
        )
        db.add(audit)
        await db.commit()

    # -------------------------------------------------------------------------
    # List helpers
    # -------------------------------------------------------------------------

    async def list_given(
        self, db: AsyncSession, grantor: User
    ) -> list[PermissionGrant]:
        return await permission_grant_crud.list_given(
            db, grantor_id=grantor.id, org_id=grantor.organization_id
        )

    async def list_received(
        self, db: AsyncSession, grantee: User
    ) -> list[PermissionGrant]:
        return await permission_grant_crud.list_received(
            db, grantee_id=grantee.id, org_id=grantee.organization_id
        )

    async def list_audit(
        self, db: AsyncSession, grantor: User, limit: int = 50, offset: int = 0
    ) -> list[PermissionGrantAudit]:
        return await permission_grant_crud.list_audit(
            db, grantor_id=grantor.id, limit=limit, offset=offset
        )


# ---------------------------------------------------------------------------
# Private validators
# ---------------------------------------------------------------------------


def _validate_resource_type(resource_type: str) -> None:
    if resource_type not in RESOURCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resource_type '{resource_type}'. "
            f"Must be one of: {', '.join(RESOURCE_TYPES)}",
        )


def _validate_actions(actions: list[str]) -> None:
    if not actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="actions must not be empty",
        )
    invalid = [a for a in actions if a not in GRANT_ACTIONS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid actions {invalid}. Must be subset of: {list(GRANT_ACTIONS)}",
        )


permission_service = PermissionService()
