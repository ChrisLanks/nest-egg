"""Budget models."""

import uuid
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    Numeric,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class BudgetPeriod(str, enum.Enum):
    """Budget period type."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Budget(Base):
    """Budget for tracking spending limits."""

    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Budget details
    name = Column(String(200), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    period = Column(SQLEnum(BudgetPeriod), nullable=False, default=BudgetPeriod.MONTHLY)

    # Category filtering (optional - if null, applies to all spending)
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Label filtering (optional - mutually exclusive with category_id)
    label_id = Column(
        UUID(as_uuid=True),
        ForeignKey("labels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Date range
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Null = ongoing

    # Settings
    rollover_unused = Column(
        Boolean, default=False, nullable=False
    )  # Roll over unused budget to next period
    alert_threshold = Column(
        Numeric(5, 2), default=Decimal("0.80"), nullable=False
    )  # Alert at 80% by default

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Shared budget (household collaboration)
    is_shared = Column(Boolean, default=False, nullable=False)
    shared_user_ids = Column(JSON, nullable=True)  # List of user UUIDs, null = all org members

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="budgets")
    label = relationship("Label")

    __table_args__ = (
        Index("ix_budgets_org_active", "organization_id", "is_active"),
        Index("ix_budgets_org_dates", "organization_id", "start_date", "end_date"),
    )
