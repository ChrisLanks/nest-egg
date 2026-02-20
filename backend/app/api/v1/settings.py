"""Settings API endpoints for user profile and organization preferences."""

from typing import Any, List, Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User, Organization
from app.schemas.user import UserUpdate, OrganizationUpdate
from app.services.password_validation_service import password_validation_service
from app.services.rate_limit_service import get_rate_limit_service

router = APIRouter()
rate_limit_service = get_rate_limit_service()


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    birth_day: Optional[int] = None
    birth_month: Optional[int] = None
    birth_year: Optional[int] = None
    is_org_admin: bool
    dashboard_layout: Optional[List[Any]] = None

    model_config = {"from_attributes": True}


class DashboardLayoutUpdate(BaseModel):
    """Request body for updating dashboard widget layout."""

    layout: List[Any]  # list of {id: str, span: 1|2} objects


class ChangePasswordRequest(BaseModel):
    """Request to change password."""

    current_password: str
    new_password: str = Field(
        ...,
        min_length=12,
        description="Password must be at least 12 characters and include uppercase, lowercase, digit, and special character",
    )


class OrganizationPreferencesResponse(BaseModel):
    """Organization preferences response."""

    id: UUID
    name: str
    monthly_start_day: int
    custom_month_end_day: int
    timezone: str

    model_config = {"from_attributes": True}


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        display_name=current_user.display_name,
        birth_day=current_user.birthdate.day if current_user.birthdate else None,
        birth_month=current_user.birthdate.month if current_user.birthdate else None,
        birth_year=current_user.birthdate.year if current_user.birthdate else None,
        is_org_admin=current_user.is_org_admin,
        dashboard_layout=current_user.dashboard_layout,
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    update_data: UserUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's profile.
    Rate limited to 10 updates per hour to prevent abuse.
    """
    # Rate limit: 10 profile updates per hour per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=3600,  # 1 hour
    )

    # Update fields
    if update_data.first_name is not None:
        current_user.first_name = update_data.first_name
    if update_data.last_name is not None:
        current_user.last_name = update_data.last_name
    if update_data.display_name is not None:
        current_user.display_name = update_data.display_name

    # Update birthday (requires day, month, and year together)
    birthday_fields = (update_data.birth_day, update_data.birth_month, update_data.birth_year)
    if all(f is not None for f in birthday_fields):
        try:
            current_user.birthdate = date(update_data.birth_year, update_data.birth_month, update_data.birth_day)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid birthday")
    elif any(f is not None for f in birthday_fields):
        raise HTTPException(status_code=400, detail="birth_day, birth_month, and birth_year must all be provided together")

    # Email update requires additional verification (not implemented here)
    if update_data.email is not None and update_data.email != current_user.email:
        # Check if email is already taken
        result = await db.execute(select(User).where(User.email == update_data.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = update_data.email
        current_user.email_verified = False  # Require re-verification

    await db.commit()
    await db.refresh(current_user)

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        display_name=current_user.display_name,
        birth_day=current_user.birthdate.day if current_user.birthdate else None,
        birth_month=current_user.birthdate.month if current_user.birthdate else None,
        birth_year=current_user.birthdate.year if current_user.birthdate else None,
        is_org_admin=current_user.is_org_admin,
        dashboard_layout=current_user.dashboard_layout,
    )


@router.put("/dashboard-layout", status_code=204)
async def update_dashboard_layout(
    body: DashboardLayoutUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save the user's customized dashboard widget layout."""
    current_user.dashboard_layout = body.layout
    await db.commit()
    return Response(status_code=204)


@router.post("/profile/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change user's password with strength validation.
    Rate limited to 10 password changes per hour to allow for legitimate
    retries (wrong current password, validation failures) while preventing abuse.
    """
    # Rate limit: 10 password changes per hour per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=3600,  # 1 hour
    )

    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password strength and check for breaches
    await password_validation_service.validate_and_raise_async(
        password_data.new_password, check_breach=True
    )

    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@router.get("/organization", response_model=OrganizationPreferencesResponse)
async def get_organization_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization preferences."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrganizationPreferencesResponse(
        id=org.id,
        name=org.name,
        monthly_start_day=org.monthly_start_day,
        custom_month_end_day=org.custom_month_end_day,
        timezone=org.timezone,
    )


@router.patch("/organization", response_model=OrganizationPreferencesResponse)
async def update_organization_preferences(
    update_data: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update organization preferences. Requires org admin."""
    if not current_user.is_org_admin:
        raise HTTPException(
            status_code=403, detail="Only organization admins can update preferences"
        )

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Update fields
    if update_data.name is not None:
        org.name = update_data.name
    if update_data.monthly_start_day is not None:
        org.monthly_start_day = update_data.monthly_start_day
    if update_data.custom_month_end_day is not None:
        org.custom_month_end_day = update_data.custom_month_end_day
    if update_data.timezone is not None:
        org.timezone = update_data.timezone

    await db.commit()
    await db.refresh(org)

    return OrganizationPreferencesResponse(
        id=org.id,
        name=org.name,
        monthly_start_day=org.monthly_start_day,
        custom_month_end_day=org.custom_month_end_day,
        timezone=org.timezone,
    )
