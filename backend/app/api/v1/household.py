"""Household management API endpoints."""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, HouseholdInvitation, InvitationStatus
from app.dependencies import get_current_admin_user

router = APIRouter(prefix="/household", tags=["household"])

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
        .where(
            User.organization_id == current_user.organization_id,
            User.is_active == True
        )
        .order_by(User.created_at)
    )
    members = result.scalars().all()
    return members


@router.post("/invite", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    request: InviteMemberRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a user to join the household. Only admins can invite."""

    # Check household size limit
    result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id,
            User.is_active == True
        )
    )
    member_count = len(result.scalars().all())

    if member_count >= MAX_HOUSEHOLD_MEMBERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Household cannot exceed {MAX_HOUSEHOLD_MEMBERS} members"
        )

    # Check if user is already a member
    result = await db.execute(
        select(User).where(
            User.email == request.email,
            User.organization_id == current_user.organization_id
        )
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this household"
        )

    # Check for pending invitation
    result = await db.execute(
        select(HouseholdInvitation).where(
            HouseholdInvitation.email == request.email,
            HouseholdInvitation.organization_id == current_user.organization_id,
            HouseholdInvitation.status == InvitationStatus.PENDING
        )
    )
    existing_invitation = result.scalar_one_or_none()
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invitation is already pending for this email"
        )

    # Create invitation
    invitation = HouseholdInvitation(
        organization_id=current_user.organization_id,
        email=request.email,
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
            HouseholdInvitation.status == InvitationStatus.PENDING
        )
        .order_by(HouseholdInvitation.created_at.desc())
    )
    invitations = result.scalars().all()

    # Fetch invited_by users
    response = []
    for inv in invitations:
        result = await db.execute(
            select(User).where(User.id == inv.invited_by_user_id)
        )
        invited_by = result.scalar_one()

        response.append({
            "id": inv.id,
            "email": inv.email,
            "invitation_code": inv.invitation_code,
            "status": inv.status,
            "expires_at": inv.expires_at,
            "created_at": inv.created_at,
            "invited_by_email": invited_by.email,
        })

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
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id
        )
    )
    user_to_remove = result.scalar_one_or_none()

    if not user_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Cannot remove yourself
    if user_to_remove.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the household"
        )

    # Cannot remove primary household member
    if user_to_remove.is_primary_household_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the primary household member"
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
            HouseholdInvitation.organization_id == current_user.organization_id
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Delete invitation
    await db.delete(invitation)
    await db.commit()

    return None
