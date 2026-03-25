"""HSA receipt model for expense tracking and reimbursement management."""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class HsaReceipt(Base):
    """
    HSA receipt model for tracking qualified medical expenses.

    Supports the "invest and reimburse later" strategy by recording expenses
    that can be reimbursed from the HSA in future years tax-free.
    """

    __tablename__ = "hsa_receipts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    expense_date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(500), nullable=False)
    # dental / vision / medical / prescription / other
    category = Column(String(100), nullable=True)

    is_reimbursed = Column(Boolean, default=False, nullable=False)
    reimbursed_at = Column(Date, nullable=True)
    tax_year = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now_lambda, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now_lambda,
        onupdate=utc_now_lambda,
        nullable=False,
    )

    def __repr__(self):
        return (
            f"<HsaReceipt {self.id} ${self.amount} {self.expense_date} "
            f"reimbursed={self.is_reimbursed}>"
        )
