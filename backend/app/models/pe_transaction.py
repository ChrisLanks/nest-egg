"""Private Equity transaction model for tracking capital calls, distributions, and NAV updates."""

import enum
import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class PETransactionType(str, enum.Enum):
    CAPITAL_CALL = "capital_call"
    DISTRIBUTION = "distribution"
    NAV_UPDATE = "nav_update"


class PETransaction(Base):
    """Track capital calls, distributions, and NAV updates for PE/PD accounts."""

    __tablename__ = "pe_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_type = Column(SQLEnum(PETransactionType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    date = Column(Date, nullable=False)
    nav_after = Column(Numeric(15, 2), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
