"""Household management API endpoints."""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, get_current_admin_user
from app.models.user import User, HouseholdInvitation, InvitationStatus
from app.services.rate_limit_service import get_rate_limit_service

router = APIRouter(prefix="/household", tags=["household"])
rate_limit_service = get_rate_limit_service()

MAX_HOUSEHOLD_MEMBERS = 5


# Schemas
class InviteMemberRequest(BaseModel):
    email: EmailStr


class HouseholdMember(BaseModel):
    id: UUID
    email: str
    display_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_org_admin: bool
    is_primary_household_member: bool
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    invitation_code: str
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
    invited_by_email: str

    class Config:
        from_attributes = True


@router.get("/members", response_model=List[HouseholdMember])
async def list_household_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members in the current user's household."""
    result = await db.execute(
        select(User)
        .where(User.organization_id == current_user.organization_id, User.is_active.is_(True))
        .order_by(User.created_at)
    )
    members = result.scalars().all()
    return members


@router.post("/invite", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    request_data: InviteMemberRequest,
    http_request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Invite a user to join the household. Only admins can invite.
    Rate limited to 5 invitations per hour to prevent spam.
    """
    # Rate limit: 5 invitations per hour per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=3600,  # 1 hour
    )

    # Check household size limit
    result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id, User.is_active.is_(True)
        )
    )
    member_count = len(result.scalars().all())

    if member_count >= MAX_HOUSEHOLD_MEMBERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Household cannot exceed {MAX_HOUSEHOLD_MEMBERS} members",
        )

    # Check if user is already a member
    result = await db.execute(
        select(User).where(
            User.email == request_data.email, User.organization_id == current_user.organization_id
        )
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this household",
        )

    # Check for pending invitation
    result = await db.execute(
        select(HouseholdInvitation).where(
            HouseholdInvitation.email == request_data.email,
            HouseholdInvitation.organization_id == current_user.organization_id,
            HouseholdInvitation.status == InvitationStatus.PENDING,
        )
    )
    existing_invitation = result.scalar_one_or_none()
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invitation is already pending for this email",
        )

    # Create invitation
    invitation = HouseholdInvitation(
        organization_id=current_user.organization_id,
        email=request_data.email,
        invited_by_user_id=current_user.id,
        invitation_code=secrets.token_urlsafe(32),
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    # Add invited_by_email for response
    invitation_dict = {
        "id": invitation.id,
        "email": invitation.email,
        "invitation_code": invitation.invitation_code,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "created_at": invitation.created_at,
        "invited_by_email": current_user.email,
    }

    # TODO: Send invitation email

    return invitation_dict


@router.get("/invitations", response_model=List[InvitationResponse])
async def list_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all pending invitations for the household."""
    result = await db.execute(
        select(HouseholdInvitation)
        .where(
            HouseholdInvitation.organization_id == current_user.organization_id,
            HouseholdInvitation.status == InvitationStatus.PENDING,
        )
        .order_by(HouseholdInvitation.created_at.desc())
    )
    invitations = result.scalars().all()

    # Fetch invited_by users
    response = []
    for inv in invitations:
        result = await db.execute(select(User).where(User.id == inv.invited_by_user_id))
        invited_by = result.scalar_one()

        response.append(
            {
                "id": inv.id,
                "email": inv.email,
                "invitation_code": inv.invitation_code,
                "status": inv.status,
                "expires_at": inv.expires_at,
                "created_at": inv.created_at,
                "invited_by_email": invited_by.email,
            }
        )

    return response


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the household. Only admins can remove members."""

    # Get user to remove
    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    )
    user_to_remove = result.scalar_one_or_none()

    if not user_to_remove:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Cannot remove yourself
    if user_to_remove.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the household",
        )

    # Cannot remove primary household member
    if user_to_remove.is_primary_household_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the primary household member",
        )

    # Soft delete by marking inactive
    user_to_remove.is_active = False
    await db.commit()

    return None


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending invitation."""

    result = await db.execute(
        select(HouseholdInvitation).where(
            HouseholdInvitation.id == invitation_id,
            HouseholdInvitation.organization_id == current_user.organization_id,
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Delete invitation
    await db.delete(invitation)
    await db.commit()

    return None


@router.get("/invitation/{invitation_code}")
async def get_invitation_details(
    invitation_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get invitation details by code (public endpoint for accepting invitations).
    Rate limited to prevent brute force guessing of invitation codes.
    """
    # Rate limit: 10 checks per minute per IP (lenient since user might mistype)
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=10,
        window_seconds=60,
    )
    result = await db.execute(
        select(HouseholdInvitation).where(HouseholdInvitation.invitation_code == invitation_code)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Get invited_by user email
    result = await db.execute(select(User).where(User.id == invitation.invited_by_user_id))
    invited_by = result.scalar_one()

    return {
        "email": invitation.email,
        "invited_by_email": invited_by.email,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
    }


@router.post("/accept/{invitation_code}", status_code=status.HTTP_200_OK)
async def accept_invitation(
    invitation_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a household invitation (public endpoint).
    Rate limited to prevent brute force attempts on invitation codes.
    """
    # Rate limit: 5 accept attempts per minute per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=5,
        window_seconds=60,
    )
    # Get invitation
    result = await db.execute(
        select(HouseholdInvitation).where(HouseholdInvitation.invitation_code == invitation_code)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check if invitation is still pending
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation has already been {invitation.status}",
        )

    # Check if invitation is expired
    if datetime.utcnow() > invitation.expires_at:
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired"
        )

    # Check if user already exists with this email
    result = await db.execute(select(User).where(User.email == invitation.email))
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account not found. Please register first with the invited email address.",
        )

    # Check if user is already in a household
    old_organization_id = existing_user.organization_id
    if old_organization_id:
        # Check if they're already in the target household
        if old_organization_id == invitation.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this household",
            )

        # Check if user is the only member in their current household
        result = await db.execute(
            select(User).where(
                User.organization_id == old_organization_id, User.is_active.is_(True)
            )
        )
        household_members = result.scalars().all()

        if len(household_members) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot accept invitation. You are not the only member in your current household. "
                "Please have other members leave first, or create a new account.",
            )

        # User is solo - migrate them and their accounts
        # Update all accounts to new organization
        from app.models.account import Account

        result = await db.execute(
            select(Account).where(
                Account.organization_id == old_organization_id, Account.user_id == existing_user.id
            )
        )
        user_accounts = result.scalars().all()

        for account in user_accounts:
            account.organization_id = invitation.organization_id

        # Update user's organization
        existing_user.organization_id = invitation.organization_id
        existing_user.is_primary_household_member = False  # Not primary in new household

        # Mark invitation as accepted before migrating
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()

        # Commit the migration FIRST to persist user's new organization
        await db.commit()

        # Now safe to delete old organization (user is already moved)
        from app.models.user import Organization

        result = await db.execute(
            select(Organization).where(Organization.id == old_organization_id)
        )
        old_org = result.scalar_one_or_none()
        if old_org:
            await db.delete(old_org)
            await db.commit()

        return {
            "message": "Invitation accepted successfully",
            "organization_id": str(invitation.organization_id),
            "accounts_migrated": len(user_accounts),
        }
    else:
        # User has no organization - simple case
        existing_user.organization_id = invitation.organization_id

        # Mark invitation as accepted
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()

        await db.commit()

        return {
            "message": "Invitation accepted successfully",
            "organization_id": str(invitation.organization_id),
            "accounts_migrated": 0,
        }
