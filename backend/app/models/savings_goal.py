"""Savings goal models."""

import uuid
from decimal import Decimal

from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, JSON, Numeric, Text, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class SavingsGoal(Base):
    """Savings goal for tracking progress toward financial targets."""

    __tablename__ = "savings_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Goal details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    # Dates
    start_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=True)  # Optional deadline

    # Linked account (optional - track specific account balance)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Auto-sync and priority
    auto_sync = Column(Boolean, default=False, nullable=False)
    priority = Column(Integer, nullable=True)

    # Status
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    is_funded = Column(Boolean, default=False, nullable=False)
    funded_at = Column(DateTime, nullable=True)

    # Shared goal (household collaboration)
    is_shared = Column(Boolean, default=False, nullable=False)
    shared_user_ids = Column(JSON, nullable=True)  # List of user UUIDs, null = all org members

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    account = relationship("Account")

    __table_args__ = (
        Index("ix_savings_goals_org_active", "organization_id", "is_completed"),
        Index("ix_savings_goals_priority", "organization_id", "priority"),
    )
