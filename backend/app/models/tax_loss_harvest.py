"""Tax-loss harvest record model for tracking harvested losses and wash sale windows."""

import enum
import uuid

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class HarvestStatus(str, enum.Enum):
    """Status of a tax-loss harvest record."""

    ACTIVE_WINDOW = "active_window"
    WINDOW_CLOSED = "window_closed"
    WASH_SALE_TRIGGERED = "wash_sale_triggered"


class TaxLossHarvestRecord(Base):
    """Records a tax-loss harvesting event with wash sale window tracking."""

    __tablename__ = "tax_loss_harvest_records"

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
        nullable=False,
        index=True,
    )
    # Sale details
    date_harvested = Column(Date, nullable=False)
    ticker_sold = Column(String(20), nullable=False)
    lot_acquisition_date = Column(Date, nullable=True)
    loss_amount = Column(Numeric(15, 2), nullable=False)  # positive = loss harvested

    # Replacement details
    replacement_ticker = Column(String(20), nullable=True)

    # Wash sale tracking
    wash_sale_window_end = Column(Date, nullable=False)  # 30 days from sale date
    status = Column(
        SQLEnum(HarvestStatus),
        default=HarvestStatus.ACTIVE_WINDOW,
        nullable=False,
    )

    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)
