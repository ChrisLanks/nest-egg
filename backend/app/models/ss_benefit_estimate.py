"""Social Security benefit estimate model for storing user-entered SSA.gov data."""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class SSBenefitEstimate(Base):
    """Stores a user's manually-entered Social Security benefit estimates from SSA.gov."""

    __tablename__ = "ss_benefit_estimates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    age_62_benefit = Column(Numeric(10, 2), nullable=True)  # Monthly benefit at 62
    age_67_benefit = Column(Numeric(10, 2), nullable=True)  # Monthly benefit at 67 (FRA)
    age_70_benefit = Column(Numeric(10, 2), nullable=True)  # Monthly benefit at 70
    as_of_year = Column(Integer, nullable=True)  # Year the estimate was generated

    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)
