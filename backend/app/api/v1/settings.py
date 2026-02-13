"""Settings API endpoints for user profile and organization preferences."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User, Organization
from app.schemas.user import User as UserSchema, UserUpdate, OrganizationUpdate

router = APIRouter()


class UserProfileResponse(BaseModel):
    """User profile response."""
    id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    is_org_admin: bool

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    """Request to change password."""
    current_password: str
    new_password: str = Field(..., min_length=8)


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
        is_org_admin=current_user.is_org_admin,
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    # Update fields
    if update_data.first_name is not None:
        current_user.first_name = update_data.first_name
    if update_data.last_name is not None:
        current_user.last_name = update_data.last_name
    if update_data.display_name is not None:
        current_user.display_name = update_data.display_name

    # Email update requires additional verification (not implemented here)
    if update_data.email is not None and update_data.email != current_user.email:
        # Check if email is already taken
        result = await db.execute(
            select(User).where(User.email == update_data.email)
        )
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
        is_org_admin=current_user.is_org_admin,
    )


@router.post("/profile/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user's password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

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
        raise HTTPException(status_code=403, detail="Only organization admins can update preferences")

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
