"""Tax lot model for per-lot cost basis tracking."""

import enum
import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class CostBasisMethod(str, enum.Enum):
    """Cost basis accounting method for selecting lots during sales."""

    FIFO = "fifo"  # First in, first out
    LIFO = "lifo"  # Last in, first out
    HIFO = "hifo"  # Highest cost in, first out
    SPECIFIC_ID = "specific_id"  # Specific lot identification


class TaxLot(Base):
    """Individual tax lot for an investment holding.

    Tracks per-lot cost basis, acquisition date, and realized gains/losses.
    Supports partial sales via remaining_quantity tracking.
    """

    __tablename__ = "tax_lots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    holding_id = Column(
        UUID(as_uuid=True),
        ForeignKey("holdings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Lot details
    acquisition_date = Column(Date, nullable=False)
    quantity = Column(Numeric(15, 6), nullable=False)
    cost_basis_per_share = Column(Numeric(15, 4), nullable=False)
    total_cost_basis = Column(Numeric(15, 2), nullable=False)
    remaining_quantity = Column(Numeric(15, 6), nullable=False)  # Decremented on partial sales

    # Closure / sale fields
    is_closed = Column(Boolean, default=False, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    sale_proceeds = Column(Numeric(15, 2), nullable=True)
    realized_gain_loss = Column(Numeric(15, 2), nullable=True)
    holding_period = Column(String(20), nullable=True)  # SHORT_TERM or LONG_TERM

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    holding = relationship("Holding", backref="tax_lots")
    account = relationship("Account", backref="tax_lots")
