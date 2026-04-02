"""User Pydantic schemas."""

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from zoneinfo import available_timezones

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

_VALID_TIMEZONES: frozenset[str] = frozenset(available_timezones())


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=12, description="Password must be at least 12 characters")


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    # Required when changing email — prevents account takeover via stolen access token
    current_password: Optional[str] = None
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_year: Optional[int] = Field(None, ge=1900, le=2100)
    default_currency: Optional[str] = Field(None, max_length=3)
    dashboard_layout: Optional[List[Any]] = None
    onboarding_goal: Optional[str] = Field(None, max_length=50)
    # 2-character US state code (e.g. "CA", "TX").  Used for state income tax
    # estimates across tax projection, FIRE metrics, and related tools.
    # Each household member may have a different state — tools that need a
    # single value use the requesting member's state.
    state_of_residence: Optional[str] = Field(None, min_length=2, max_length=2)
    # State the user plans to retire in (may differ from current state).
    target_retirement_state: Optional[str] = Field(None, min_length=2, max_length=2)
    # UI mode preference — synced across devices via API
    show_advanced_nav: Optional[bool] = None

    @field_validator("state_of_residence", "target_retirement_state", mode="before")
    @classmethod
    def uppercase_state(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_birthday(self) -> "UserUpdate":
        """Validate that the combination of day/month/year forms a real calendar date."""
        if (
            self.birth_day is not None
            and self.birth_month is not None
            and self.birth_year is not None
        ):
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
    onboarding_completed: bool = False
    onboarding_goal: Optional[str] = None
    dashboard_layout: Optional[List[Any]] = None
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    show_advanced_nav: bool = False
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

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in _VALID_TIMEZONES:
            raise ValueError(
                f"'{v}' is not a valid IANA timezone. "
                "Use a value like 'America/New_York' or 'UTC'."
            )
        return v


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

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_TIMEZONES:
            raise ValueError(
                f"'{v}' is not a valid IANA timezone. "
                "Use a value like 'America/New_York' or 'UTC'."
            )
        return v


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
