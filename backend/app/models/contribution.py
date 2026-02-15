"""Account contribution model for recurring contributions and payments."""

import uuid
from datetime import date
from decimal import Decimal
import enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Boolean, Date, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class ContributionType(str, enum.Enum):
    """Type of recurring contribution."""
    FIXED_AMOUNT = "fixed_amount"  # Fixed dollar amount
    SHARES = "shares"  # Number of shares
    PERCENTAGE_GROWTH = "percentage_growth"  # Interest/growth percentage


class ContributionFrequency(str, enum.Enum):
    """Frequency of recurring contributions."""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class AccountContribution(Base):
    """Recurring contribution or payment for manual accounts."""

    __tablename__ = "account_contributions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Contribution details
    contribution_type = Column(SQLEnum(ContributionType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)  # Dollar amount, share count, or percentage
    frequency = Column(SQLEnum(ContributionFrequency), default=ContributionFrequency.MONTHLY, nullable=False)

    # Date range
    start_date = Column(Date, nullable=False, default=date.today)
    end_date = Column(Date, nullable=True)  # Optional end date

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Optional notes
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    account = relationship("Account", backref="contributions")
