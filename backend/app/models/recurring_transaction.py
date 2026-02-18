"""Recurring transaction detection models."""

import uuid
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    Enum as SQLEnum,
    Index,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class RecurringFrequency(str, enum.Enum):
    """Frequency of recurring transaction."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RecurringTransaction(Base):
    """Detected or manually created recurring transaction pattern."""

    __tablename__ = "recurring_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pattern details
    merchant_name = Column(String(255), nullable=False, index=True)
    description_pattern = Column(String(500), nullable=True)  # Regex or pattern for matching
    frequency = Column(SQLEnum(RecurringFrequency), nullable=False)
    average_amount = Column(Numeric(15, 2), nullable=False)
    amount_variance = Column(
        Numeric(15, 2), default=Decimal("5.00"), nullable=False
    )  # Allow +/- $5 by default

    # Category assignment (auto-apply to matched transactions)
    category_id = Column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    # Detection
    is_user_created = Column(Boolean, default=False, nullable=False)  # Manual vs auto-detected
    confidence_score = Column(Numeric(5, 2), nullable=True)  # 0.00-1.00 for auto-detected patterns

    # Tracking
    first_occurrence = Column(Date, nullable=False)
    last_occurrence = Column(Date, nullable=True)
    next_expected_date = Column(Date, nullable=True)
    occurrence_count = Column(Integer, default=1, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Bill Reminder fields
    is_bill = Column(Boolean, default=False, nullable=False)  # Mark as a bill requiring reminders
    reminder_days_before = Column(
        Integer, default=3, nullable=False
    )  # Days before due date to remind

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    account = relationship("Account")
    category = relationship("Category")

    __table_args__ = (
        Index("ix_recurring_org_merchant", "organization_id", "merchant_name"),
        Index("ix_recurring_org_active", "organization_id", "is_active"),
    )
