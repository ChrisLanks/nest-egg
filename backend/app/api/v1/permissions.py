"""Permission grant management endpoints.

These endpoints let a household member (grantor) delegate fine-grained access
to their own resources to another household member (grantee).

Key security rules enforced here:
  - resource_type "permission" is never allowed (cannot delegate grant ability)
  - grantee must be in the same org as the grantor
  - only the grantor or an org admin may update/revoke a grant
  - audit log is only readable by the owner of the grants (grantor view)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.permission import RESOURCE_TYPES
from app.models.user import User
from app.schemas.permission import (
    AuditResponse,
    GrantCreate,
    GrantResponse,
    GrantUpdate,
    HouseholdMemberResponse,
)
from app.services.permission_service import permission_service

router = APIRouter()


def _ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _display_name(user: User) -> Optional[str]:
    if user.display_name:
        return user.display_name
    parts = [p for p in [user.first_name, user.last_name] if p]
    return " ".join(parts) if parts else user.email


async def _enrich_grants(grants, db: AsyncSession) -> list[GrantResponse]:
    """Fetch display names for grantors/grantees and return GrantResponse list."""
    user_ids = set()
    for g in grants:
        user_ids.add(g.grantor_id)
        user_ids.add(g.grantee_id)

    users: dict[UUID, User] = {}
    if user_ids:
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in result.scalars().all():
            users[u.id] = u

    out = []
    for g in grants:
        r = GrantResponse.model_validate(g)
        if g.grantor_id in users:
            r.grantor_display_name = _display_name(users[g.grantor_id])
        if g.grantee_id in users:
            r.grantee_display_name = _display_name(users[g.grantee_id])
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------


@router.get("/given", response_model=list[GrantResponse])
async def list_given(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active grants the current user has given to others."""
    grants = await permission_service.list_given(db, grantor=current_user)
    return await _enrich_grants(grants, db)


@router.get("/received", response_model=list[GrantResponse])
async def list_received(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active grants others have given to the current user."""
    grants = await permission_service.list_received(db, grantee=current_user)
    return await _enrich_grants(grants, db)


@router.get("/audit", response_model=list[AuditResponse])
async def list_audit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Audit log of all grant changes where the current user is the grantor."""
    entries = await permission_service.list_audit(db, grantor=current_user)
    return [AuditResponse.model_validate(e) for e in entries]


@router.get("/members", response_model=list[HouseholdMemberResponse])
async def list_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List household members available as grantees (excludes the current user)."""
    result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id,
            User.is_active.is_(True),
            User.id != current_user.id,
        )
    )
    members = result.scalars().all()
    return [HouseholdMemberResponse.model_validate(m) for m in members]


@router.get("/resource-types", response_model=list[str])
async def list_resource_types(current_user: User = Depends(get_current_user)):
    """Return the list of grantable resource types."""
    return list(RESOURCE_TYPES)


# ---------------------------------------------------------------------------
# Write endpoints
# ---------------------------------------------------------------------------


@router.post("/grants", response_model=GrantResponse, status_code=status.HTTP_201_CREATED)
async def create_grant(
    body: GrantCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create (or update) a permission grant.

    The current user must be the data owner (grantor).  The grantee must be a
    member of the same household.  ``resource_type='permission'`` is rejected.
    """
    if body.resource_type == "permission":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Granting 'permission' delegation is not allowed",
        )

    # Verify grantee is in the same org
    result = await db.execute(
        select(User).where(
            User.id == body.grantee_id,
            User.organization_id == current_user.organization_id,
            User.is_active.is_(True),
        )
    )
    grantee = result.scalar_one_or_none()
    if grantee is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Grantee not found or not a member of your household",
        )

    if body.grantee_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot grant permissions to yourself",
        )

    grant = await permission_service.grant(
        db,
        grantor=current_user,
        grantee_id=body.grantee_id,
        resource_type=body.resource_type,
        actions=list(body.actions),
        resource_id=body.resource_id,
        expires_at=body.expires_at,
        ip_address=_ip(request),
    )
    enriched = await _enrich_grants([grant], db)
    return enriched[0]


@router.put("/grants/{grant_id}", response_model=GrantResponse)
async def update_grant(
    grant_id: UUID,
    body: GrantUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the actions and/or expiry on an existing grant."""
    from app.crud.permission import permission_grant_crud

    existing = await permission_grant_crud.get_by_id(db, grant_id)
    if existing is None or not existing.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")

    if existing.grantor_id != current_user.id and not current_user.is_org_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the grantor or an org admin may modify this grant",
        )

    # Re-use the service grant() which performs an upsert
    grant = await permission_service.grant(
        db,
        grantor=current_user,
        grantee_id=existing.grantee_id,
        resource_type=existing.resource_type,
        actions=list(body.actions),
        resource_id=existing.resource_id,
        expires_at=body.expires_at,
        ip_address=_ip(request),
    )
    enriched = await _enrich_grants([grant], db)
    return enriched[0]


@router.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_grant(
    grant_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (deactivate) a permission grant."""
    await permission_service.revoke(
        db,
        grantor=current_user,
        grant_id=grant_id,
        ip_address=_ip(request),
    )
