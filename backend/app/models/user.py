"""User and Organization models."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class Organization(Base):
    """Organization (tenant) model for multi-tenancy."""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    custom_month_end_day = Column(Integer, default=30, nullable=False)
    monthly_start_day = Column(Integer, default=1, nullable=False)  # Day of month to start tracking (1-31)
    timezone = Column(String(50), default="UTC", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name}>"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    display_name = Column(String(255))  # Optional display name
    is_active = Column(Boolean, default=True, nullable=False)
    is_org_admin = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class RefreshToken(Base):
    """Refresh token model for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken for user {self.user_id}>"

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at is not None
