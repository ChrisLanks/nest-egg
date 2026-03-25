"""Beneficiary model for estate and account beneficiary planning."""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class Beneficiary(Base):
    """
    Beneficiary designation for an account or overall estate.

    Tracks primary and contingent beneficiaries with percentage allocations.
    When account_id is NULL, represents an estate-level (not account-specific)
    beneficiary designation.
    """

    __tablename__ = "beneficiaries"

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

    name = Column(String(255), nullable=False)
    # spouse / child / trust / charity / other
    relationship = Column(String(100), nullable=False)
    # primary / contingent
    designation_type = Column(String(20), nullable=False)
    percentage = Column(Numeric(5, 2), nullable=False)
    dob = Column(Date, nullable=True)
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
            f"<Beneficiary {self.name} {self.designation_type} "
            f"{self.percentage}% account={self.account_id}>"
        )
