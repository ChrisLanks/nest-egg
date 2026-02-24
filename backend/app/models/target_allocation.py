"""Target allocation models for portfolio rebalancing."""

import uuid
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class TargetAllocation(Base):
    """Target portfolio allocation for rebalancing analysis."""

    __tablename__ = "target_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
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

    # Allocation details
    name = Column(String(200), nullable=False)
    allocations = Column(JSON, nullable=False)  # List of {asset_class, target_percent, label}
    drift_threshold = Column(
        Numeric(5, 2), default=Decimal("5.0"), nullable=False
    )  # Percentage threshold before rebalancing is needed

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    __table_args__ = (
        Index("ix_target_allocations_org_user", "organization_id", "user_id"),
    )
