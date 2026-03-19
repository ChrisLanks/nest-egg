"""User and Organization models."""

import enum
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.services.encryption_service import EncryptedDate
from app.utils.datetime_utils import utc_now, utc_now_lambda


class InvitationStatus(str, enum.Enum):
    """Invitation status enum."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class GuestRole(str, enum.Enum):
    """Role assigned to a household guest."""

    VIEWER = "viewer"  # Read-only access
    ADVISOR = "advisor"  # Can edit (with PermissionGrant)


class GuestInvitationStatus(str, enum.Enum):
    """Status of a guest invitation."""

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
    default_currency = Column(String(3), default="USD", nullable=False, server_default="USD")
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
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    email_notifications_enabled = Column(Boolean, default=True, nullable=False)

    # Account security fields
    failed_login_attempts = Column(
        Integer, default=0, nullable=False
    )  # Track failed login attempts
    locked_until = Column(
        DateTime, nullable=True
    )  # Account locked until this time (NULL = not locked)

    # Onboarding wizard tracking
    onboarding_completed = Column(Boolean, default=False, nullable=False, server_default="false")
    onboarding_step = Column(
        String(50), nullable=True
    )  # current step: "profile", "accounts", "budget", "goals"

    # Customizable dashboard layout — list of {id, span} objects; NULL = default layout
    dashboard_layout = Column(JSON, nullable=True)

    # Per-category notification preferences — {category: bool}; missing key = enabled
    # Categories: account_syncs, account_activity, budget_alerts, milestones, household
    notification_preferences = Column(JSON, nullable=True, default=dict)

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
    consents = relationship("UserConsent", back_populates="user", cascade="all, delete-orphan")
    identities = relationship("UserIdentity", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.id}>"


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
        return f"<HouseholdInvitation {self.id} to org {self.organization_id}>"

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
        return (
            f"<AccountShare account={self.account_id}"
            f" shared_with={self.shared_with_user_id}"
            f" permission={self.permission}>"
        )


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
    version = Column(String(50), nullable=False)  # e.g. "2024-01" — bump when T&C/PP changes
    consented_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6; NULL if unavailable
    revoked_at = Column(DateTime, nullable=True)  # NULL = consent currently active

    # Relationships
    user = relationship("User", back_populates="consents")

    def __repr__(self):
        return f"<UserConsent user={self.user_id} type={self.consent_type} version={self.version}>"


class HouseholdGuest(Base):
    """
    Guest access record: allows a user to view another household's data
    without becoming a member. The guest's own accounts/data never appear
    in the host household.
    """

    __tablename__ = "household_guests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    role = Column(
        SQLEnum(GuestRole, name="guest_role"),
        nullable=False,
        default=GuestRole.VIEWER,
    )
    label = Column(String(100), nullable=True)  # Display name: "Mom & Dad", "Kids"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_guest_user_org"),
        Index("ix_household_guest_user_org_active", "user_id", "organization_id", "is_active"),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization")
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_id])

    def __repr__(self):
        return f"<HouseholdGuest user={self.user_id} org={self.organization_id} role={self.role}>"


class HouseholdGuestInvitation(Base):
    """Invitation for guest access to a household (does NOT make user a member)."""

    __tablename__ = "household_guest_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email = Column(String(255), nullable=False)
    invited_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    invitation_code = Column(String(64), nullable=False, unique=True, index=True)
    role = Column(
        SQLEnum(GuestRole, name="guest_role"),
        nullable=False,
        default=GuestRole.VIEWER,
    )
    label = Column(String(100), nullable=True)
    status = Column(
        SQLEnum(GuestInvitationStatus, name="guest_invitation_status"),
        nullable=False,
        default=GuestInvitationStatus.PENDING,
    )
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    __table_args__ = (
        Index("ix_guest_invitation_email_org_status", "email", "organization_id", "status"),
    )

    # Relationships
    organization = relationship("Organization")
    invited_by = relationship("User", foreign_keys=[invited_by_id])

    def __repr__(self):
        return f"<HouseholdGuestInvitation {self.id} to org {self.organization_id}>"

    @property
    def is_expired(self) -> bool:
        return utc_now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.status == GuestInvitationStatus.PENDING and not self.is_expired
