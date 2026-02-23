"""User and Organization models."""

import uuid
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.services.encryption_service import EncryptedDate
from app.utils.datetime_utils import utc_now_lambda, utc_now


class InvitationStatus(str, enum.Enum):
    """Invitation status enum."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class SharePermission(str, enum.Enum):
    """Account share permission enum."""

    VIEW = "view"
    EDIT = "edit"


class Organization(Base):
    """Organization (tenant) model for multi-tenancy."""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    custom_month_end_day = Column(Integer, default=30, nullable=False)
    monthly_start_day = Column(
        Integer, default=1, nullable=False
    )  # Day of month to start tracking (1-31)
    timezone = Column(String(50), default="UTC", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    report_templates = relationship(
        "ReportTemplate", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Organization {self.name}>"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    display_name = Column(String(255))  # Optional display name

    # Retirement planning fields
    birthdate = Column(EncryptedDate, nullable=True)  # Encrypted at rest (GDPR Art. 32)
    target_retirement_date = Column(Date, nullable=True)  # Planned retirement date

    is_active = Column(Boolean, default=True, nullable=False)
    is_org_admin = Column(Boolean, default=False, nullable=False)
    is_primary_household_member = Column(
        Boolean, default=False, nullable=False
    )  # First user who created org
    email_verified = Column(Boolean, default=False, nullable=False)

    # Account security fields
    failed_login_attempts = Column(
        Integer, default=0, nullable=False
    )  # Track failed login attempts
    locked_until = Column(
        DateTime, nullable=True
    )  # Account locked until this time (NULL = not locked)

    # Customizable dashboard layout — list of {id, span} objects; NULL = default layout
    dashboard_layout = Column(JSON, nullable=True)

    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    mfa = relationship(
        "UserMFA", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    consents = relationship(
        "UserConsent", back_populates="user", cascade="all, delete-orphan"
    )
    identities = relationship(
        "UserIdentity", back_populates="user", cascade="all, delete-orphan"
    )

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
        return utc_now() > self.expires_at

    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at is not None


class HouseholdInvitation(Base):
    """Household invitation model for inviting users to join an organization."""

    __tablename__ = "household_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email = Column(String(255), nullable=False)
    invited_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    invitation_code = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(
        SQLEnum(InvitationStatus, name="invitation_status"),
        nullable=False,
        default=InvitationStatus.PENDING,
    )
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    # Relationships
    organization = relationship("Organization")
    invited_by = relationship("User", foreign_keys=[invited_by_user_id])

    def __repr__(self):
        return f"<HouseholdInvitation {self.email} to org {self.organization_id}>"

    @property
    def is_expired(self) -> bool:
        """Check if invitation is expired."""
        return utc_now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if invitation is still valid (pending and not expired)."""
        return self.status == InvitationStatus.PENDING and not self.is_expired


class EmailVerificationToken(Base):
    """Token used to verify (or re-verify) a user's email address."""

    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # SHA-256 hex digest of the raw token — never store the raw token
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    user = relationship("User")

    def __repr__(self):
        return f"<EmailVerificationToken user={self.user_id}>"

    @property
    def is_valid(self) -> bool:
        """Token is valid if it has not been used and has not expired."""
        return self.used_at is None and utc_now() < self.expires_at


class PasswordResetToken(Base):
    """Token used to reset a user's password via email link."""

    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # SHA-256 hex digest of the raw token — never store the raw token
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    user = relationship("User")

    def __repr__(self):
        return f"<PasswordResetToken user={self.user_id}>"

    @property
    def is_valid(self) -> bool:
        """Token is valid if it has not been used and has not expired."""
        return self.used_at is None and utc_now() < self.expires_at


class AccountShare(Base):
    """Account share model for sharing accounts between household members."""

    __tablename__ = "account_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    shared_with_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    permission = Column(
        SQLEnum(SharePermission, name="share_permission"),
        nullable=False,
        default=SharePermission.VIEW,
    )
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    # Add unique constraint
    __table_args__ = (
        UniqueConstraint("account_id", "shared_with_user_id", name="uq_account_user_share"),
    )

    # Relationships
    shared_with = relationship("User", foreign_keys=[shared_with_user_id])

    def __repr__(self):
        return f"<AccountShare account={self.account_id} shared_with={self.shared_with_user_id} permission={self.permission}>"


class ConsentType(str, enum.Enum):
    """Types of user consent that must be captured."""

    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    MARKETING = "marketing"


class UserConsent(Base):
    """
    Record of user consent events for GDPR/CCPA compliance.

    A row is written for each consent action (accept or revoke).
    Consent is considered active when revoked_at IS NULL.
    """

    __tablename__ = "user_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_type = Column(String(50), nullable=False)
    version = Column(String(50), nullable=False)   # e.g. "2024-01" — bump when T&C/PP changes
    consented_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6; NULL if unavailable
    revoked_at = Column(DateTime, nullable=True)    # NULL = consent currently active

    # Relationships
    user = relationship("User", back_populates="consents")

    def __repr__(self):
        return f"<UserConsent user={self.user_id} type={self.consent_type} version={self.version}>"
