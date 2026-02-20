"""User Pydantic schemas."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_year: Optional[int] = Field(None, ge=1900, le=2100)

    @model_validator(mode="after")
    def validate_birthday(self) -> "UserUpdate":
        """Validate that the combination of day/month/year forms a real calendar date."""
        if self.birth_day is not None and self.birth_month is not None and self.birth_year is not None:
            try:
                date(self.birth_year, self.birth_month, self.birth_day)
            except ValueError as exc:
                raise ValueError(f"Invalid birthday: {exc}") from exc
        return self


class UserInDB(UserBase):
    """User schema as stored in database."""

    id: UUID
    organization_id: UUID
    is_active: bool
    is_org_admin: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class User(UserInDB):
    """User schema for API responses."""


class OrganizationBase(BaseModel):
    """Base organization schema."""

    name: str = Field(..., min_length=1, max_length=255)
    custom_month_end_day: int = Field(default=30, ge=1, le=31)
    monthly_start_day: int = Field(
        default=1, ge=1, le=28, description="Day of month to start monthly tracking (1-28)"
    )
    timezone: str = Field(default="UTC")


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    custom_month_end_day: Optional[int] = Field(None, ge=1, le=31)
    monthly_start_day: Optional[int] = Field(
        None, ge=1, le=28, description="Day of month to start monthly tracking (1-28)"
    )
    timezone: Optional[str] = None


class OrganizationInDB(OrganizationBase):
    """Organization schema as stored in database."""

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Organization(OrganizationInDB):
    """Organization schema for API responses."""
