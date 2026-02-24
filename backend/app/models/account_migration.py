"""Account provider migration audit log."""

import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class MigrationStatus(str, enum.Enum):
    """Status of a migration operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AccountMigrationLog(Base):
    """Immutable audit log for account provider migrations.

    Every migration attempt (success or failure) is recorded here.
    This provides a complete history of provider changes for each account.
    """

    __tablename__ = "account_migration_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    initiated_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Migration details
    source_provider = Column(String(20), nullable=False)
    target_provider = Column(String(20), nullable=False)
    status = Column(
        SQLEnum(MigrationStatus, native_enum=False),
        nullable=False,
        default=MigrationStatus.PENDING,
    )

    # Snapshot of account state before/after migration
    pre_migration_snapshot = Column(JSON, nullable=False)
    post_migration_snapshot = Column(JSON, nullable=True)

    # New provider enrollment (PlaidItem.id / TellerEnrollment.id / MxMember.id)
    target_enrollment_id = Column(UUID(as_uuid=True), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamps
    initiated_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    account = relationship("Account")
    initiated_by = relationship("User")

    __table_args__ = (
        Index("ix_migration_log_account", "account_id"),
        Index("ix_migration_log_org_date", "organization_id", "initiated_at"),
        Index("ix_migration_log_org_id", "organization_id"),
    )
