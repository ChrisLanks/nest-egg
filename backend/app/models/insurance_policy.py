"""Insurance policy model for tracking household insurance coverage."""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class PolicyType(str, enum.Enum):
    """Insurance policy types."""

    TERM_LIFE = "term_life"
    WHOLE_LIFE = "whole_life"
    UNIVERSAL_LIFE = "universal_life"
    DISABILITY_SHORT_TERM = "disability_short_term"
    DISABILITY_LONG_TERM = "disability_long_term"
    UMBRELLA = "umbrella"
    HOMEOWNERS = "homeowners"
    RENTERS = "renters"
    AUTO = "auto"
    HEALTH = "health"
    DENTAL = "dental"
    VISION = "vision"
    LONG_TERM_CARE = "long_term_care"
    OTHER = "other"


class InsurancePolicy(Base):
    """Insurance policy for a household member."""

    __tablename__ = "insurance_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    policy_type = Column(SQLEnum(PolicyType), nullable=False)
    provider = Column(String(200), nullable=True)
    policy_number = Column(String(100), nullable=True)
    coverage_amount = Column(Numeric(15, 2), nullable=True)  # death benefit / coverage limit
    annual_premium = Column(Numeric(10, 2), nullable=True)
    monthly_premium = Column(Numeric(10, 2), nullable=True)
    deductible = Column(Numeric(10, 2), nullable=True)
    effective_date = Column(Date, nullable=True)
    expiration_date = Column(Date, nullable=True)  # null = permanent policy
    beneficiary_name = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)
