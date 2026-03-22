"""Household guest access API endpoints.

Allows users to invite guests to view (or advise on) their household
without making them full members. Guests keep their own household and
accounts separate — only the host household's data is visible.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.dependencies import get_current_admin_user, get_current_user
from app.models.user import (
    GuestInvitationStatus,
    GuestRole,
    HouseholdGuest,
    HouseholdGuestInvitation,
    Organization,
    User,
)
from app.services.email_service import email_service
from app.services.rate_limit_service import get_rate_limit_service
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()
rate_limit_service = get_rate_limit_service()

GUEST_INVITATION_EXPIRY_DAYS = 7
MAX_GUEST_INVITATIONS_PER_HOUR = 5
MAX_GUEST_REVOCATIONS_PER_HOUR = 20  # Prevent bulk-revocation abuse


# ─── Schemas ───────────────────────────────────────────────────────────────


class InviteGuestRequest(BaseModel):
    email: EmailStr
    role: GuestRole = GuestRole.VIEWER
    label: Optional[str] = Field(None, max_length=100)
    access_expires_days: Optional[int] = Field(
        None, ge=1, le=365, description="Days until guest access expires (optional)"
    )


class UpdateGuestRequest(BaseModel):
    role: Optional[GuestRole] = None
    label: Optional[str] = Field(None, max_length=100)
    expires_at: Optional[datetime] = None
    access_expires_days: Optional[int] = Field(None, ge=1, le=365)


class GuestResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str
    organization_id: UUID
    role: GuestRole
    label: Optional[str]
    is_active: bool
    created_at: datetime
    revoked_at: Optional[datetime]
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GuestInvitationResponse(BaseModel):
    id: UUID
    email: str
    role: GuestRole
    label: Optional[str]
    status: GuestInvitationStatus
    expires_at: datetime
    created_at: datetime
    join_url: str
    email_delivered: bool = True

    class Config:
        from_attributes = True


class MyHouseholdResponse(BaseModel):
    organization_id: UUID
    organization_name: str
    role: GuestRole
    label: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class InvitationPreviewResponse(BaseModel):
    organization_name: str
    invited_by_email: str  # masked
    role: GuestRole
    label: Optional[str]
    expires_at: datetime


def _mask_email(email: str) -> str:
    """Mask email for public display: j***n@g***.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    domain_name, tld = domain.rsplit(".", 1) if "." in domain else (domain, "")
    masked_local = local[0] + "***" + (local[-1] if len(local) > 1 else "")
    masked_domain = domain_name[0] + "***" + ("." + tld if tld else "")
    return f"{masked_local}@{masked_domain}"


# ─── Host admin endpoints ──────────────────────────────────────────────────


@router.post("/invite", response_model=GuestInvitationResponse, status_code=201)
async def invite_guest(
    body: InviteGuestRequest,
    request: Request,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a user as a guest to this household (admin only)."""
    # Rate limit
    rate_key = f"guest_invite:{admin.id}"
    allowed = await rate_limit_service.check_rate_limit(
        rate_key, MAX_GUEST_INVITATIONS_PER_HOUR, 3600
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many guest invitations. Please try again later.",
        )

    # Cannot invite yourself
    if body.email.lower() == admin.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite yourself as a guest",
        )

    # Check if already an active guest
    result = await db.execute(
        select(HouseholdGuest)
        .join(User, HouseholdGuest.user_id == User.id)
        .where(
            User.email == body.email.lower(),
            HouseholdGuest.organization_id == admin.organization_id,
            HouseholdGuest.is_active.is_(True),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already an active guest of this household",
        )

    # Check for pending invitation
    result = await db.execute(
        select(HouseholdGuestInvitation).where(
            HouseholdGuestInvitation.email == body.email.lower(),
            HouseholdGuestInvitation.organization_id == admin.organization_id,
            HouseholdGuestInvitation.status == GuestInvitationStatus.PENDING,
        )
    )
    existing_invite = result.scalar_one_or_none()
    if existing_invite and not existing_invite.is_expired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email",
        )

    # Expire any stale pending invitations for this email+org
    if existing_invite:
        existing_invite.status = GuestInvitationStatus.EXPIRED

    # Create invitation
    invitation_code = secrets.token_urlsafe(32)
    invitation = HouseholdGuestInvitation(
        organization_id=admin.organization_id,
        email=body.email.lower(),
        invited_by_id=admin.id,
        invitation_code=invitation_code,
        role=body.role,
        label=body.label,
        status=GuestInvitationStatus.PENDING,
        expires_at=utc_now() + timedelta(days=GUEST_INVITATION_EXPIRY_DAYS),
        created_at=utc_now(),
        access_expires_days=body.access_expires_days,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    join_url = f"{settings.APP_BASE_URL}/guest-access/accept/{invitation_code}"

    email_delivered = True
    try:
        org_name_result = await db.execute(
            select(Organization.name).where(Organization.id == admin.organization_id)
        )
        household_name = org_name_result.scalar_one()
        await email_service.send_invitation_email(
            to_email=body.email,
            invitation_code=invitation_code,
            inviter_name=admin.display_name or admin.email,
            household_name=household_name,
        )
    except Exception:
        email_delivered = False
        logger.warning(
            "Failed to send guest invitation email to %s for org %s",
            body.email,
            admin.organization_id,
            exc_info=True,
        )

    return GuestInvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        label=invitation.label,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        join_url=join_url,
        email_delivered=email_delivered,
    )


@router.get("/guests", response_model=List[GuestResponse])
async def list_guests(
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all guests in the current household (admin only)."""
    result = await db.execute(
        select(HouseholdGuest, User.email)
        .join(User, HouseholdGuest.user_id == User.id)
        .where(
            HouseholdGuest.organization_id == admin.organization_id,
            HouseholdGuest.is_active.is_(True),
        )
        .order_by(HouseholdGuest.created_at.desc())
    )
    rows = result.all()

    return [
        GuestResponse(
            id=guest.id,
            user_id=guest.user_id,
            user_email=email,
            organization_id=guest.organization_id,
            role=guest.role,
            label=guest.label,
            is_active=guest.is_active,
            created_at=guest.created_at,
            revoked_at=guest.revoked_at,
            expires_at=guest.expires_at,
        )
        for guest, email in rows
    ]


@router.delete("/guests/{guest_id}", status_code=204)
async def revoke_guest(
    guest_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a guest's access (admin only). Takes effect immediately."""
    # Rate limit: 20 revocations per hour to prevent bulk-locking out collaborators
    rate_key = f"guest_revoke:{admin.id}"
    allowed = await rate_limit_service.check_rate_limit(
        rate_key, MAX_GUEST_REVOCATIONS_PER_HOUR, 3600
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many revocation requests. Please try again later.",
        )

    result = await db.execute(
        select(HouseholdGuest).where(
            HouseholdGuest.id == guest_id,
            HouseholdGuest.organization_id == admin.organization_id,
            HouseholdGuest.is_active.is_(True),
        )
    )
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    guest.is_active = False
    guest.revoked_at = utc_now()
    guest.revoked_by_id = admin.id
    await db.commit()


@router.patch("/guests/{guest_id}", response_model=GuestResponse)
async def update_guest(
    guest_id: UUID,
    body: UpdateGuestRequest,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a guest's role or label (admin only)."""
    result = await db.execute(
        select(HouseholdGuest).where(
            HouseholdGuest.id == guest_id,
            HouseholdGuest.organization_id == admin.organization_id,
            HouseholdGuest.is_active.is_(True),
        )
    )
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    if body.role is not None:
        guest.role = body.role
    if body.label is not None:
        guest.label = body.label
    if body.expires_at is not None:
        guest.expires_at = body.expires_at
    elif body.access_expires_days is not None:
        guest.expires_at = utc_now() + timedelta(days=body.access_expires_days)

    await db.commit()
    await db.refresh(guest)

    # Get email for response
    user_result = await db.execute(select(User.email).where(User.id == guest.user_id))
    user_email = user_result.scalar_one()

    return GuestResponse(
        id=guest.id,
        user_id=guest.user_id,
        user_email=user_email,
        organization_id=guest.organization_id,
        role=guest.role,
        label=guest.label,
        is_active=guest.is_active,
        created_at=guest.created_at,
        revoked_at=guest.revoked_at,
        expires_at=guest.expires_at,
    )


@router.get("/invitations", response_model=List[GuestInvitationResponse])
async def list_invitations(
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List pending guest invitations (admin only)."""
    result = await db.execute(
        select(HouseholdGuestInvitation)
        .where(
            HouseholdGuestInvitation.organization_id == admin.organization_id,
            HouseholdGuestInvitation.status == GuestInvitationStatus.PENDING,
        )
        .order_by(HouseholdGuestInvitation.created_at.desc())
    )
    invitations = result.scalars().all()

    return [
        GuestInvitationResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            label=inv.label,
            status=inv.status if not inv.is_expired else GuestInvitationStatus.EXPIRED,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            join_url=f"{settings.APP_BASE_URL}/guest-access/accept/{inv.invitation_code}",
        )
        for inv in invitations
    ]


@router.delete("/invitations/{invitation_id}", status_code=204)
async def cancel_invitation(
    invitation_id: UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending guest invitation (admin only)."""
    result = await db.execute(
        select(HouseholdGuestInvitation).where(
            HouseholdGuestInvitation.id == invitation_id,
            HouseholdGuestInvitation.organization_id == admin.organization_id,
            HouseholdGuestInvitation.status == GuestInvitationStatus.PENDING,
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invitation.status = GuestInvitationStatus.EXPIRED
    await db.commit()


# ─── Guest-facing endpoints ────────────────────────────────────────────────


@router.get("/my-households", response_model=List[MyHouseholdResponse])
async def my_guest_households(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all households the current user has guest access to."""
    result = await db.execute(
        select(HouseholdGuest, Organization.name)
        .join(Organization, HouseholdGuest.organization_id == Organization.id)
        .where(
            HouseholdGuest.user_id == current_user.id,
            HouseholdGuest.is_active.is_(True),
        )
        .order_by(Organization.name)
    )
    rows = result.all()

    return [
        MyHouseholdResponse(
            organization_id=guest.organization_id,
            organization_name=org_name,
            role=guest.role,
            label=guest.label,
            is_active=guest.is_active,
        )
        for guest, org_name in rows
    ]


@router.post("/accept/{code}")
async def accept_guest_invitation(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a guest invitation using the invitation code."""
    # Lock the invitation row to prevent concurrent acceptance
    result = await db.execute(
        select(HouseholdGuestInvitation)
        .where(
            HouseholdGuestInvitation.invitation_code == code,
        )
        .with_for_update()
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.status != GuestInvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation has already been {invitation.status.value}",
        )

    if invitation.is_expired:
        invitation.status = GuestInvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Invitation email must match the current user
    if invitation.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address",
        )

    # Cannot be a guest of your own household
    if invitation.organization_id == current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this household",
        )

    # Check if already an active guest (maybe re-invited after revoke)
    result = await db.execute(
        select(HouseholdGuest).where(
            HouseholdGuest.user_id == current_user.id,
            HouseholdGuest.organization_id == invitation.organization_id,
        )
    )
    existing_guest = result.scalar_one_or_none()

    # Compute guest expiry from invitation's access_expires_days
    guest_expires_at = None
    if invitation.access_expires_days:
        guest_expires_at = utc_now() + timedelta(days=invitation.access_expires_days)

    if existing_guest:
        if existing_guest.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have active guest access to this household",
            )
        # Re-activate revoked guest record
        existing_guest.is_active = True
        existing_guest.role = invitation.role
        existing_guest.label = invitation.label
        existing_guest.revoked_at = None
        existing_guest.revoked_by_id = None
        existing_guest.invited_by_id = invitation.invited_by_id
        existing_guest.expires_at = guest_expires_at
    else:
        guest = HouseholdGuest(
            user_id=current_user.id,
            organization_id=invitation.organization_id,
            invited_by_id=invitation.invited_by_id,
            role=invitation.role,
            label=invitation.label,
            created_at=utc_now(),
            expires_at=guest_expires_at,
        )
        db.add(guest)

    invitation.status = GuestInvitationStatus.ACCEPTED
    invitation.accepted_at = utc_now()
    await db.commit()

    return {"detail": "Guest access granted successfully"}


@router.post("/decline/{code}")
async def decline_guest_invitation(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Decline a guest invitation."""
    result = await db.execute(
        select(HouseholdGuestInvitation).where(
            HouseholdGuestInvitation.invitation_code == code,
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address",
        )

    if invitation.status != GuestInvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation has already been {invitation.status.value}",
        )

    invitation.status = GuestInvitationStatus.DECLINED
    await db.commit()

    return {"detail": "Invitation declined"}


@router.delete("/leave/{org_id}", status_code=204)
async def leave_guest_household(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leave a household you have guest access to."""
    result = await db.execute(
        select(HouseholdGuest).where(
            HouseholdGuest.user_id == current_user.id,
            HouseholdGuest.organization_id == org_id,
            HouseholdGuest.is_active.is_(True),
        )
    )
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=404, detail="No active guest access found")

    guest.is_active = False
    guest.revoked_at = utc_now()
    guest.revoked_by_id = current_user.id
    await db.commit()


# ─── Public endpoint (rate-limited) ────────────────────────────────────────


@router.get("/invitation/{code}", response_model=InvitationPreviewResponse)
async def preview_invitation(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Preview a guest invitation (public, rate-limited).

    Rate limit is kept intentionally tight: invitation codes are 32-byte
    URL-safe tokens (~192 bits of entropy), but we still limit enumeration
    attempts to reduce oracle surface. We always return the same 404 detail
    regardless of whether the code exists, is expired, or is already used —
    so an attacker cannot distinguish valid-but-used from never-existed.
    """
    # 5 previews per hour per IP — tighter than before (was 20).
    # Legitimate users follow an emailed link; they don't need many attempts.
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=5,
        window_seconds=3600,
    )

    result = await db.execute(
        select(HouseholdGuestInvitation).where(
            HouseholdGuestInvitation.invitation_code == code,
        )
    )
    invitation = result.scalar_one_or_none()
    # Use a single generic message for all failure cases to avoid leaking
    # information about which codes exist, are expired, or are already used.
    _not_found = HTTPException(status_code=404, detail="Invitation not found or expired")
    if not invitation or invitation.status != GuestInvitationStatus.PENDING:
        raise _not_found

    if invitation.is_expired:
        raise _not_found

    # Get org name and inviter email
    org_result = await db.execute(
        select(Organization.name).where(Organization.id == invitation.organization_id)
    )
    org_name = org_result.scalar_one()

    inviter_email = ""
    if invitation.invited_by_id:
        inviter_result = await db.execute(
            select(User.email).where(User.id == invitation.invited_by_id)
        )
        inviter_email = inviter_result.scalar_one_or_none() or ""

    return InvitationPreviewResponse(
        organization_name=org_name,
        invited_by_email=_mask_email(inviter_email) if inviter_email else "",
        role=invitation.role,
        label=invitation.label,
        expires_at=invitation.expires_at,
    )
