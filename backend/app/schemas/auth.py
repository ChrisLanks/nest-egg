"""Authentication Pydantic schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import User


class RegisterRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        description="Password must be at least 12 characters and include uppercase, lowercase, digit, and special character"
    )
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    organization_name: str = Field(..., min_length=1, max_length=255)


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
