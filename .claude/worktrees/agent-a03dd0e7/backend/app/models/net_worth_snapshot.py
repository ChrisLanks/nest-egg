"""Net worth snapshot model for historical tracking."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class NetWorthSnapshot(Base):
    """
    Net worth snapshot model for historical tracking.

    Captures the full net worth breakdown at a point in time.
    One snapshot per organization per user per day.
    When user_id is NULL, represents the combined household net worth.
    """

    __tablename__ = "net_worth_snapshots"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    snapshot_date = Column(Date, nullable=False)

    # Net worth totals
    total_net_worth = Column(Numeric(15, 2), nullable=False)
    total_assets = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    total_liabilities = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))

    # Asset breakdown by category
    cash_and_checking = Column(Numeric(15, 2), default=Decimal("0"))
    savings = Column(Numeric(15, 2), default=Decimal("0"))
    investments = Column(Numeric(15, 2), default=Decimal("0"))
    retirement = Column(Numeric(15, 2), default=Decimal("0"))
    property = Column(Numeric(15, 2), default=Decimal("0"))
    vehicles = Column(Numeric(15, 2), default=Decimal("0"))
    other_assets = Column(Numeric(15, 2), default=Decimal("0"))

    # Liability breakdown by category
    credit_cards = Column(Numeric(15, 2), default=Decimal("0"))
    loans = Column(Numeric(15, 2), default=Decimal("0"))
    mortgages = Column(Numeric(15, 2), default=Decimal("0"))
    student_loans = Column(Numeric(15, 2), default=Decimal("0"))
    other_debts = Column(Numeric(15, 2), default=Decimal("0"))

    # Per-account breakdown (JSON for flexibility)
    breakdown_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utc_now_lambda)

    # Partial unique indexes handle the nullable user_id correctly:
    # - uq_org_user_snapshot_date: one per-user snapshot per day (WHERE user_id IS NOT NULL)
    # - uq_org_household_snapshot_date: one household snapshot per day (WHERE user_id IS NULL)
    # Indexes are created in the Alembic migration; __table_args__ declares them for metadata.
    __table_args__ = (
        Index(
            "uq_org_user_snapshot_date",
            "organization_id",
            "user_id",
            "snapshot_date",
            unique=True,
            postgresql_where="user_id IS NOT NULL",
        ),
        Index(
            "uq_org_household_snapshot_date",
            "organization_id",
            "snapshot_date",
            unique=True,
            postgresql_where="user_id IS NULL",
        ),
    )

    def __repr__(self):
        user = self.user_id or "household"
        return (
            f"<NetWorthSnapshot {self.organization_id} {user} "
            f"{self.snapshot_date} ${self.total_net_worth}>"
        )
