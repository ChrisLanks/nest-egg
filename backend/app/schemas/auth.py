"""Authentication Pydantic schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.user import User


class RegisterRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        description="Password must be at least 12 characters and include uppercase, lowercase, digit, and special character",
    )
    display_name: str = Field(..., min_length=1)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_name: str = Field("My Household", min_length=1, max_length=255)
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_year: Optional[int] = Field(None, ge=1900, le=2100)
    skip_breach_check: bool = Field(False, description="Skip the breach check — user accepts the risk")

    @model_validator(mode="after")
    def validate_birthday(self) -> "RegisterRequest":
        """Validate that the combination of day/month/year forms a real calendar date."""
        if self.birth_day is not None and self.birth_month is not None and self.birth_year is not None:
            try:
                date(self.birth_year, self.birth_month, self.birth_day)
            except ValueError as exc:
                raise ValueError(f"Invalid birthday: {exc}") from exc
        return self


class LoginRequest(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: User


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class AccessTokenResponse(BaseModel):
    """Schema for access token response."""

    access_token: str
    token_type: str = "bearer"
