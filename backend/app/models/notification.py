"""Notification model for user alerts."""

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SQLEnum
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
    MILESTONE = "milestone"
    ALL_TIME_HIGH = "all_time_high"
    HOUSEHOLD_MEMBER_JOINED = "household_member_joined"
    HOUSEHOLD_MEMBER_LEFT = "household_member_left"
    EXPENSE_SPLIT_ASSIGNED = "expense_split_assigned"   # a split was assigned to you
    SETTLEMENT_REMINDER = "settlement_reminder"         # outstanding balance due between members
    GOAL_COMPLETED = "goal_completed"
    GOAL_FUNDED = "goal_funded"
    FIRE_COAST_FI = "fire_coast_fi"
    FIRE_INDEPENDENT = "fire_independent"
    RETIREMENT_SCENARIO_STALE = "retirement_scenario_stale"
    WEEKLY_RECAP = "weekly_recap"
    EQUITY_VESTING = "equity_vesting"
    CRYPTO_PRICE_ALERT = "crypto_price_alert"
    EQUITY_AMT_WARNING = "equity_amt_warning"
    HSA_CONTRIBUTION_LIMIT = "hsa_contribution_limit"
    BOND_MATURITY_UPCOMING = "bond_maturity_upcoming"
    BENEFICIARY_MISSING = "beneficiary_missing"
    TAX_BUCKET_IMBALANCE = "tax_bucket_imbalance"
    HARVEST_OPPORTUNITY = "harvest_opportunity"
    PRO_RATA_WARNING = "pro_rata_warning"
    RMD_TAX_BOMB_WARNING = "rmd_tax_bomb_warning"
    BILL_DUE_BEFORE_PAYCHECK = "bill_due_before_paycheck"
    PENSION_ELECTION_DEADLINE = "pension_election_deadline"
    REBALANCE_DRIFT_ALERT = "rebalance_drift_alert"
    QCD_OPPORTUNITY = "qcd_opportunity"
    NAV_FEATURE_UNLOCKED = "nav_feature_unlocked"


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

    # Email delivery tracking (None = no email attempted, True = sent, False = failed)
    email_sent = Column(Boolean, nullable=True, default=None)

    # Action URL (optional link for user to take action)
    action_url = Column(String(500), nullable=True)
    action_label = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)  # Auto-dismiss after this time

    __table_args__ = (
        # Composite indexes for common query patterns
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_org_created", "organization_id", "created_at"),
        Index("ix_notifications_user_is_read", "user_id", "is_read"),
        Index("ix_notifications_org_dismissed", "organization_id", "is_dismissed"),
        # Covering index for the most-common dashboard query:
        # "give me unread notifications for this user, newest first"
        # Avoids a separate is_read filter pass after the user_id lookup.
        Index("ix_notifications_user_unread_created", "user_id", "is_read", "created_at"),
    )

    # Relationships
    organization = relationship("Organization")
    user = relationship("User")

    def __repr__(self):
        return f"<Notification {self.type} - {self.title}>"
