"""Dividend and investment income tracking model."""

import enum
import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class IncomeType(str, enum.Enum):
    """Types of investment income."""

    DIVIDEND = "dividend"  # Cash dividend payment
    QUALIFIED_DIVIDEND = "qualified_dividend"  # Qualified (lower tax rate)
    CAPITAL_GAIN_DISTRIBUTION = "capital_gain_distribution"  # Fund CG distribution
    RETURN_OF_CAPITAL = "return_of_capital"  # ROC (reduces cost basis)
    INTEREST = "interest"  # Bond interest / money market
    REINVESTED_DIVIDEND = "reinvested_dividend"  # DRIP reinvestment


class DividendIncome(Base):
    """Investment income event: dividends, distributions, and interest."""

    __tablename__ = "dividend_income"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    holding_id = Column(
        UUID(as_uuid=True),
        ForeignKey("holdings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Income details
    income_type = Column(SQLEnum(IncomeType), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    name = Column(String(255), nullable=True)

    # Amounts
    amount = Column(Numeric(15, 2), nullable=False)  # Total income received
    per_share_amount = Column(Numeric(10, 6), nullable=True)  # Per-share dividend
    shares_held = Column(Numeric(15, 6), nullable=True)  # Shares at ex-date

    # Key dates
    ex_date = Column(Date, nullable=True, index=True)  # Ex-dividend date
    pay_date = Column(Date, nullable=True)  # Payment date
    record_date = Column(Date, nullable=True)  # Record date

    # Reinvestment tracking (for DRIP)
    is_reinvested = Column(Boolean, default=False, nullable=False)
    reinvested_shares = Column(Numeric(15, 6), nullable=True)
    reinvested_price = Column(Numeric(15, 4), nullable=True)

    # Currency
    currency = Column(String(3), default="USD", nullable=False, server_default="USD")

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    account = relationship("Account")
    holding = relationship("Holding")
