"""Dependent model for tracking household dependents (children, parents, etc.)."""

import uuid

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class Dependent(Base):
    """A dependent in the household (child, parent, other)."""

    __tablename__ = "dependents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    relationship = Column(String(50), nullable=False)  # "child", "parent", "other"
    expected_college_start_year = Column(Integer, nullable=True)
    expected_college_cost_annual = Column(Numeric(10, 2), nullable=True)  # in today's dollars
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)
