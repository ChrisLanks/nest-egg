"""Household management API endpoints."""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants.financial import HOUSEHOLD
from app.core.database import get_db
from app.dependencies import get_current_admin_user, get_current_user
from app.models.account import Account
from app.models.budget import Budget
from app.models.notification import NotificationPriority, NotificationType
from app.models.permission import PermissionGrant
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction
from app.models.user import HouseholdInvitation, InvitationStatus, Organization, User
from app.services.email_service import email_service
from app.services.notification_service import NotificationService
from app.services.rate_limit_service import get_rate_limit_service
from app.utils.datetime_utils import utc_now

router = APIRouter(prefix="/household", tags=["household"])
rate_limit_service = get_rate_limit_service()


def _mask_email(email: str) -> str:
    """Mask email for public display: j***n@g***.com"""
    local, domain = email.split("@", 1)
    domain_name, tld = domain.rsplit(".", 1)
    masked_local = local[0] + "***" + (local[-1] if len(local) > 1 else "")
    masked_domain = domain_name[0] + "***" + "." + tld
    return f"{masked_local}@{masked_domain}"


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
    birth_year: Optional[int] = None
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
    join_url: str  # Always returned; share directly if email is not configured

    class Config:
        from_attributes = True


class ResendInvitationResponse(BaseModel):
    id: str
    email: str
    expires_at: datetime
    join_url: str


class LeaveHouseholdResponse(BaseModel):
    message: str


class InvitationDetailsResponse(BaseModel):
    email: str
    invited_by_name: str
    status: InvitationStatus
    expires_at: datetime


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
    return [
        HouseholdMember(
            id=m.id,
            email=m.email,
            display_name=m.display_name,
            first_name=m.first_name,
            last_name=m.last_name,
            is_org_admin=m.is_org_admin,
            is_primary_household_member=m.is_primary_household_member,
            birth_year=m.birthdate.year if m.birthdate else None,
            created_at=m.created_at,
        )
        for m in members
    ]


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
    # Rate limit: 5 invitations per hour per user (not per-IP so IP rotation can't bypass)
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=3600,  # 1 hour
        identifier=str(current_user.id),
    )

    # Check household size limit
    result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(User.organization_id == current_user.organization_id, User.is_active.is_(True))
    )
    member_count = result.scalar_one()

    if member_count >= HOUSEHOLD.MAX_MEMBERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Household cannot exceed {HOUSEHOLD.MAX_MEMBERS} members",
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

    # Replace any existing pending invitation for this email (re-invite is allowed).
    # Use a bulk DELETE to avoid lazy-loading the invitation's relationships.
    await db.execute(
        delete(HouseholdInvitation).where(
            HouseholdInvitation.email == request_data.email,
            HouseholdInvitation.organization_id == current_user.organization_id,
            HouseholdInvitation.status == InvitationStatus.PENDING,
        )
    )

    # Create invitation
    invitation = HouseholdInvitation(
        organization_id=current_user.organization_id,
        email=request_data.email,
        invited_by_user_id=current_user.id,
        invitation_code=secrets.token_urlsafe(32),
        status=InvitationStatus.PENDING,
        expires_at=utc_now() + timedelta(days=HOUSEHOLD.INVITATION_EXPIRY_DAYS),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    join_url = f"{settings.APP_BASE_URL}/accept-invite?code={invitation.invitation_code}"

    # Get org name for email without triggering a lazy-load on the async session
    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = org_result.scalar_one_or_none()
    org_name = org.name if org else "your household"

    # Send invitation email (non-blocking; still return 201 if email fails)
    await email_service.send_invitation_email(
        to_email=invitation.email,
        invitation_code=invitation.invitation_code,
        invited_by=current_user.display_name or current_user.email,
        org_name=org_name,
    )

    return {
        "id": invitation.id,
        "email": invitation.email,
        "invitation_code": invitation.invitation_code,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "created_at": invitation.created_at,
        "invited_by_email": current_user.email,
        "join_url": join_url,
    }


@router.get("/invitations", response_model=List[InvitationResponse])
async def list_invitations(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all pending invitations for the household (admin only)."""
    result = await db.execute(
        select(HouseholdInvitation)
        .where(
            HouseholdInvitation.organization_id == current_user.organization_id,
            HouseholdInvitation.status == InvitationStatus.PENDING,
        )
        .order_by(HouseholdInvitation.created_at.desc())
    )
    invitations = result.scalars().all()

    # Batch-fetch invited_by users to avoid N+1 queries
    inviter_ids = list({inv.invited_by_user_id for inv in invitations})
    if inviter_ids:
        user_result = await db.execute(select(User).where(User.id.in_(inviter_ids)))
        users_by_id = {u.id: u for u in user_result.scalars().all()}
    else:
        users_by_id = {}

    response = []
    for inv in invitations:
        invited_by = users_by_id.get(inv.invited_by_user_id)

        response.append(
            {
                "id": inv.id,
                "email": inv.email,
                "invitation_code": inv.invitation_code,
                "status": inv.status,
                "expires_at": inv.expires_at,
                "created_at": inv.created_at,
                "invited_by_email": invited_by.email if invited_by else "unknown",
                "join_url": f"{settings.APP_BASE_URL}/accept-invite?code={inv.invitation_code}",
            }
        )

    return response


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the household. Only admins can remove members."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=10, window_seconds=3600, identifier=str(current_user.id)
    )

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

    # Revoke all permission grants where this user is the grantor or grantee.
    # The FK has ondelete=CASCADE but the user row is soft-deleted, so we must
    # clean up grants explicitly to prevent dangling access.
    await db.execute(
        delete(PermissionGrant).where(
            PermissionGrant.organization_id == current_user.organization_id,
            (PermissionGrant.grantor_id == user_id)
            | (PermissionGrant.grantee_id == user_id),
        )
    )

    # Archive selective retirement scenarios that include this member
    from app.services.retirement.retirement_planner_service import (
        RetirementPlannerService,
    )

    member_name = user_to_remove.display_name or user_to_remove.email or "a member"
    await RetirementPlannerService.archive_scenarios_for_departed_member(
        db,
        str(current_user.organization_id),
        str(user_id),
        departed_user_name=member_name,
    )

    await db.commit()

    # Notify remaining household members
    await NotificationService.create_notification(
        db=db,
        organization_id=current_user.organization_id,
        type=NotificationType.HOUSEHOLD_MEMBER_LEFT,
        title=f"{member_name} was removed from the household",
        message=(
            f"{member_name} has been removed. "
            "Their accounts are no longer part of your shared finances."
        ),
        priority=NotificationPriority.MEDIUM,
        action_url="/settings",
        action_label="View Household",
        expires_in_days=14,
    )

    return None


class UpdateMemberRoleRequest(BaseModel):
    is_admin: bool


@router.patch("/members/{user_id}/role", response_model=HouseholdMember)
async def update_member_role(
    user_id: UUID,
    body: UpdateMemberRoleRequest,
    http_request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Promote or demote a household member. Only admins can change roles."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=10, window_seconds=3600, identifier=str(current_user.id)
    )

    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Cannot change your own role
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    # Cannot demote the primary household member
    if target_user.is_primary_household_member and not body.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote the primary household member",
        )

    target_user.is_org_admin = body.is_admin
    await db.commit()
    await db.refresh(target_user)

    return target_user


class UpdateMemberStatusRequest(BaseModel):
    is_active: bool


@router.patch("/members/{user_id}/status", response_model=HouseholdMember)
async def update_member_status(
    user_id: UUID,
    body: UpdateMemberStatusRequest,
    http_request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a household member's login. Only admins can change status.

    Setting is_active=False prevents the user from logging in.
    Setting is_active=True re-enables their account.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=10, window_seconds=3600, identifier=str(current_user.id)
    )

    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Cannot disable yourself
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own status",
        )

    # Cannot disable the primary household member
    if target_user.is_primary_household_member and not body.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable the primary household member",
        )

    target_user.is_active = body.is_active

    # Handle retirement scenario archival on member status change
    if not body.is_active:
        from app.services.retirement.retirement_planner_service import (
            RetirementPlannerService,
        )

        member_name = target_user.display_name or target_user.email or "a member"
        await RetirementPlannerService.archive_scenarios_for_departed_member(
            db,
            str(current_user.organization_id),
            str(user_id),
            departed_user_name=member_name,
        )

    await db.commit()
    await db.refresh(target_user)

    return target_user


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    invitation_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending invitation."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=20, window_seconds=3600, identifier=str(current_user.id)
    )

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


@router.post("/invitations/{invitation_id}/resend", status_code=status.HTTP_200_OK, response_model=ResendInvitationResponse)
async def resend_invitation(
    invitation_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resend (and refresh) a pending invitation.

    Generates a new invitation code and extends the expiry by 7 days, then
    re-sends the invitation email.  Only admins can resend invitations.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=3600,
        identifier=str(current_user.id),
    )

    result = await db.execute(
        select(HouseholdInvitation).where(
            HouseholdInvitation.id == invitation_id,
            HouseholdInvitation.organization_id == current_user.organization_id,
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending invitations can be resent",
        )

    # Refresh code and expiry
    invitation.invitation_code = secrets.token_urlsafe(32)
    invitation.expires_at = utc_now() + timedelta(days=HOUSEHOLD.INVITATION_EXPIRY_DAYS)
    await db.commit()
    await db.refresh(invitation)

    join_url = f"{settings.APP_BASE_URL}/accept-invite?code={invitation.invitation_code}"

    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = org_result.scalar_one_or_none()
    org_name = org.name if org else "your household"

    await email_service.send_invitation_email(
        to_email=invitation.email,
        invitation_code=invitation.invitation_code,
        invited_by=current_user.display_name or current_user.email,
        org_name=org_name,
    )

    return {
        "id": str(invitation.id),
        "email": invitation.email,
        "expires_at": invitation.expires_at,
        "join_url": join_url,
    }


@router.post("/leave", status_code=status.HTTP_200_OK, response_model=LeaveHouseholdResponse)
async def leave_household(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Leave the current household and move to a new solo household.

    The primary household member cannot leave — they created the household
    and must remove other members first. All accounts owned by the leaving
    user are moved to their new solo household.
    """
    # Check if user is the only member in the household
    member_count_result = await db.execute(
        select(func.count(User.id)).where(
            User.organization_id == current_user.organization_id,
            User.is_active.is_(True),
        )
    )
    member_count = member_count_result.scalar()

    if member_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot leave a household where you are the only member.",
        )

    if current_user.is_primary_household_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The primary household member cannot leave. Remove other members first.",
        )

    # Expire any pending invitations for this user so the admin can re-invite cleanly
    await db.execute(
        update(HouseholdInvitation)
        .where(
            HouseholdInvitation.email == current_user.email,
            HouseholdInvitation.organization_id == current_user.organization_id,
            HouseholdInvitation.status == InvitationStatus.PENDING,
        )
        .values(status=InvitationStatus.EXPIRED)
    )

    # Build a sensible name for their new solo household
    name_part = (
        current_user.display_name or current_user.first_name or current_user.email.split("@")[0]
    )
    new_org = Organization(name=f"{name_part}'s Household")
    db.add(new_org)
    await db.flush()  # resolve new_org.id without committing yet

    # Move accounts that belong to this user
    result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.user_id == current_user.id,
        )
    )
    user_accounts = result.scalars().all()
    for account in user_accounts:
        # Migrate transactions to new org before moving the account
        await db.execute(
            update(Transaction)
            .where(Transaction.account_id == account.id)
            .values(organization_id=new_org.id)
        )
        account.organization_id = new_org.id

    # ---- Copy shared budgets the leaving user had access to ----
    user_id_str = str(current_user.id)
    migrated_account_ids = {str(a.id) for a in user_accounts}

    shared_budgets_result = await db.execute(
        select(Budget).where(
            Budget.organization_id == current_user.organization_id,
            Budget.is_shared.is_(True),
        )
    )
    for budget in shared_budgets_result.scalars().all():
        # Check if the user had access: shared_user_ids is null (all) or includes the user
        if budget.shared_user_ids is not None and user_id_str not in budget.shared_user_ids:
            continue
        # Copy the budget to the new org
        new_budget = Budget(
            organization_id=new_org.id,
            name=budget.name,
            amount=budget.amount,
            period=budget.period,
            start_date=budget.start_date,
            end_date=budget.end_date,
            category_id=budget.category_id,
            label_id=budget.label_id,
            rollover_unused=budget.rollover_unused,
            alert_threshold=budget.alert_threshold,
            is_active=budget.is_active,
            is_shared=False,  # Not shared in new solo household
            shared_user_ids=None,
        )
        db.add(new_budget)

    # ---- Copy shared goals the leaving user had access to ----
    shared_goals_result = await db.execute(
        select(SavingsGoal).where(
            SavingsGoal.organization_id == current_user.organization_id,
            SavingsGoal.is_shared.is_(True),
        )
    )
    for goal in shared_goals_result.scalars().all():
        if goal.shared_user_ids is not None and user_id_str not in goal.shared_user_ids:
            continue
        # For goals with linked accounts, only copy if the user owns that account
        if goal.account_id and str(goal.account_id) not in migrated_account_ids:
            continue
        new_goal = SavingsGoal(
            organization_id=new_org.id,
            name=goal.name,
            description=goal.description,
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
            start_date=goal.start_date,
            target_date=goal.target_date,
            account_id=goal.account_id
            if goal.account_id and str(goal.account_id) in migrated_account_ids
            else None,
            auto_sync=goal.auto_sync
            if goal.account_id and str(goal.account_id) in migrated_account_ids
            else False,
            is_shared=False,
            shared_user_ids=None,
        )
        db.add(new_goal)

    # Notify old household before moving the user
    leaver_name = current_user.display_name or current_user.first_name or current_user.email
    await NotificationService.create_notification(
        db=db,
        organization_id=current_user.organization_id,
        type=NotificationType.HOUSEHOLD_MEMBER_LEFT,
        title=f"{leaver_name} left the household",
        message=f"{leaver_name} has left your household. Their accounts have been moved.",
        priority=NotificationPriority.MEDIUM,
        action_url="/settings",
        action_label="View Household",
        expires_in_days=14,
    )

    # Re-home the user
    current_user.organization_id = new_org.id
    current_user.is_primary_household_member = True
    current_user.is_org_admin = True

    await db.commit()
    return {
        "message": (
            "You have left the household." " Your accounts have been moved to your new household."
        )
    }


@router.get("/invitation/{invitation_code}", response_model=InvitationDetailsResponse)
async def get_invitation_details(
    invitation_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get invitation details by code (public endpoint for accepting invitations).
    Rate limited to prevent brute force guessing of invitation codes.

    Uses a single generic 404 for all failure modes (not found, expired, used)
    to avoid leaking information about which codes exist.
    """
    # Rate limit: 5 checks per hour per IP (was 10/min = 600/hr).
    # Legitimate users follow an emailed link and only need one lookup.
    # The tighter window prevents timing-oracle enumeration.
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=5,
        window_seconds=3600,
    )
    result = await db.execute(
        select(HouseholdInvitation).where(HouseholdInvitation.invitation_code == invitation_code)
    )
    invitation = result.scalar_one_or_none()

    _not_found = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found or expired"
    )
    if not invitation:
        raise _not_found

    # Get invited_by user email
    result = await db.execute(select(User).where(User.id == invitation.invited_by_user_id))
    invited_by = result.scalar_one_or_none()

    return {
        "email": _mask_email(invitation.email),
        "invited_by_name": (invited_by.display_name or invited_by.first_name or "A household member") if invited_by else "A household member",
        "status": invitation.status,
        "expires_at": invitation.expires_at,
    }


@router.post("/accept/{invitation_code}", status_code=status.HTTP_200_OK)
async def accept_invitation(
    invitation_code: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a household invitation (requires authentication).
    The authenticated user's email must match the invitation email.
    Rate limited to prevent brute force attempts on invitation codes.
    """
    # Rate limit: 5 accept attempts per minute per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=5,
        window_seconds=60,
    )
    # Get invitation with row-level lock to prevent concurrent double-acceptance
    result = await db.execute(
        select(HouseholdInvitation)
        .where(HouseholdInvitation.invitation_code == invitation_code)
        .with_for_update()
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
    if utc_now() > invitation.expires_at:
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired"
        )

    # Verify the authenticated user matches the invitation recipient
    if current_user.email != invitation.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address",
        )

    existing_user = current_user

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
                detail=(
                    "Cannot accept invitation. You are not the only member"
                    " in your current household. Please have other members"
                    " leave first, or create a new account."
                ),
            )

        # User is solo - migrate them and their accounts
        # Update all accounts to new organization
        result = await db.execute(
            select(Account).where(
                Account.organization_id == old_organization_id, Account.user_id == existing_user.id
            )
        )
        user_accounts = result.scalars().all()

        for account in user_accounts:
            # Migrate transactions to new org before moving the account
            await db.execute(
                update(Transaction)
                .where(Transaction.account_id == account.id)
                .values(organization_id=invitation.organization_id)
            )
            account.organization_id = invitation.organization_id

        # Update user's organization
        existing_user.organization_id = invitation.organization_id
        existing_user.is_primary_household_member = False  # Not primary in new household
        existing_user.is_org_admin = False  # Invited members join as regular members

        # Mark invitation as accepted before migrating
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = utc_now()

        # Commit the migration FIRST to persist user's new organization
        await db.commit()

        # Now safe to delete old organization (user is already moved)
        result = await db.execute(
            select(Organization).where(Organization.id == old_organization_id)
        )
        old_org = result.scalar_one_or_none()
        if old_org:
            await db.delete(old_org)
            await db.commit()

        # Notify household that a new member joined
        joiner_name = existing_user.display_name or existing_user.first_name or existing_user.email
        await NotificationService.create_notification(
            db=db,
            organization_id=invitation.organization_id,
            type=NotificationType.HOUSEHOLD_MEMBER_JOINED,
            title=f"{joiner_name} joined your household!",
            message=f"{joiner_name} has accepted the invitation and joined your household.",
            priority=NotificationPriority.MEDIUM,
            action_url="/settings",
            action_label="View Household",
            expires_in_days=14,
        )

        return {
            "message": "Invitation accepted successfully",
            "organization_id": str(invitation.organization_id),
            "accounts_migrated": len(user_accounts),
        }
    else:
        # User has no organization - simple case
        existing_user.organization_id = invitation.organization_id
        existing_user.is_org_admin = False  # Invited members join as regular members

        # Mark invitation as accepted
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = utc_now()

        await db.commit()

        # Notify household that a new member joined
        joiner_name = existing_user.display_name or existing_user.first_name or existing_user.email
        await NotificationService.create_notification(
            db=db,
            organization_id=invitation.organization_id,
            type=NotificationType.HOUSEHOLD_MEMBER_JOINED,
            title=f"{joiner_name} joined your household!",
            message=f"{joiner_name} has accepted the invitation and joined your household.",
            priority=NotificationPriority.MEDIUM,
            action_url="/settings",
            action_label="View Household",
            expires_in_days=14,
        )

        return {
            "message": "Invitation accepted successfully",
            "organization_id": str(invitation.organization_id),
            "accounts_migrated": 0,
        }
