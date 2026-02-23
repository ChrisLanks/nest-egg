"""Holdings model for investment accounts."""

import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class Holding(Base):
    """Investment holding (stock, bond, ETF, etc.)."""

    __tablename__ = "holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Holding identification
    ticker = Column(String(20), nullable=False)  # Stock symbol (e.g., "AAPL", "VTSAX")
    name = Column(String(255), nullable=True)  # Full name (e.g., "Apple Inc.")

    # Quantity
    shares = Column(Numeric(15, 6), nullable=False)  # Support fractional shares

    # Cost basis
    cost_basis_per_share = Column(Numeric(15, 2), nullable=True)  # What you paid per share
    total_cost_basis = Column(Numeric(15, 2), nullable=True)  # Total amount paid

    # Current value (cached, refreshed periodically)
    current_price_per_share = Column(Numeric(15, 2), nullable=True)
    current_total_value = Column(Numeric(15, 2), nullable=True)
    price_as_of = Column(DateTime, nullable=True, index=True)  # When the price was last fetched

    # Asset classification
    asset_type = Column(
        String(50), nullable=True
    )  # 'stock', 'bond', 'etf', 'mutual_fund', 'cash', 'other'
    asset_class = Column(
        String(50), nullable=True
    )  # 'domestic', 'international', 'bond', 'cash', 'other'
    market_cap = Column(String(20), nullable=True)  # 'large', 'mid', 'small', null for non-equity
    sector = Column(
        String(100), nullable=True
    )  # Financial sector (e.g., 'Technology', 'Healthcare', 'Financials')
    industry = Column(
        String(100), nullable=True
    )  # Industry within sector (e.g., 'Software', 'Biotechnology')
    country = Column(
        String(100), nullable=True
    )  # Country of domicile (e.g., 'USA', 'Germany', 'China')

    # Fees
    expense_ratio = Column(
        Numeric(5, 4), nullable=True
    )  # Annual expense ratio as decimal (e.g., 0.0003 = 0.03%)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="holdings")
