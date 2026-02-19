"""Notification model for user alerts."""

import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class NotificationType(str, enum.Enum):
    """Type of notification."""

    SYNC_FAILED = "sync_failed"
    REAUTH_REQUIRED = "reauth_required"
    SYNC_STALE = "sync_stale"
    ACCOUNT_CONNECTED = "account_connected"
    ACCOUNT_ERROR = "account_error"
    BUDGET_ALERT = "budget_alert"
    TRANSACTION_DUPLICATE = "transaction_duplicate"
    LARGE_TRANSACTION = "large_transaction"


class NotificationPriority(str, enum.Enum):
    """Priority level of notification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """User notifications for alerts and system messages."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Notification details
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    priority = Column(
        SQLEnum(NotificationPriority), default=NotificationPriority.MEDIUM, nullable=False
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Related entity (e.g., account_id for sync failures)
    related_entity_type = Column(String(50), nullable=True)  # 'account', 'transaction', 'budget'
    related_entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Status
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_dismissed = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # Action URL (optional link for user to take action)
    action_url = Column(String(500), nullable=True)
    action_label = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)  # Auto-dismiss after this time

    # Relationships
    organization = relationship("Organization")
    user = relationship("User")

    def __repr__(self):
        return f"<Notification {self.type} - {self.title}>"
