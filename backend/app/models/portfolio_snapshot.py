"""Portfolio snapshot model for historical tracking."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class PortfolioSnapshot(Base):
    """
    Portfolio snapshot model for historical tracking.

    Captures the portfolio state at a point in time for performance tracking.
    One snapshot per organization per day per user (NULL user_id = whole household).
    """

    __tablename__ = "portfolio_snapshots"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    snapshot_date = Column(Date, nullable=False)

    # Portfolio totals
    total_value = Column(Numeric(15, 2), nullable=False)
    total_cost_basis = Column(Numeric(15, 2), nullable=True)
    total_gain_loss = Column(Numeric(15, 2), nullable=True)
    total_gain_loss_percent = Column(Numeric(10, 4), nullable=True)

    # Asset allocation breakdown
    stocks_value = Column(Numeric(15, 2), default=Decimal("0"))
    bonds_value = Column(Numeric(15, 2), default=Decimal("0"))
    etf_value = Column(Numeric(15, 2), default=Decimal("0"))
    mutual_funds_value = Column(Numeric(15, 2), default=Decimal("0"))
    cash_value = Column(Numeric(15, 2), default=Decimal("0"))
    other_value = Column(Numeric(15, 2), default=Decimal("0"))

    # Category breakdown (retirement vs taxable)
    retirement_value = Column(Numeric(15, 2), default=Decimal("0"))
    taxable_value = Column(Numeric(15, 2), default=Decimal("0"))

    # Geographic breakdown
    domestic_value = Column(Numeric(15, 2), default=Decimal("0"))
    international_value = Column(Numeric(15, 2), default=Decimal("0"))

    # Full snapshot data (JSONB for flexibility)
    # Contains complete PortfolioSummary for historical drill-down
    snapshot_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utc_now_lambda)

    # Unique constraints: one snapshot per org/date/user combination.
    # NULL user_id = household-level snapshot.
    # Partial unique indexes (uq_org_snapshot_date_user, uq_org_snapshot_date_household)
    # are managed in the Alembic migration since they require WHERE clauses.
    __table_args__ = ()

    def __repr__(self):
        return (
            f"<PortfolioSnapshot {self.organization_id} {self.snapshot_date} ${self.total_value}>"
        )
