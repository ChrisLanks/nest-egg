"""Authentication Pydantic schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

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
