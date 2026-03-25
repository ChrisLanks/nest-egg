"""Charitable donation model for tracking and optimizing charitable giving."""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CharitableDonation(Base):
    """Tracks charitable donations for tax optimization (QCD, bunching, appreciated securities)."""

    __tablename__ = "charitable_donations"

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

    donation_date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    organization_name = Column(String(255), nullable=False)
    donation_type = Column(String(50), nullable=False)  # cash/daf/qcd/appreciated_securities/property
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=True,
    )
    security_symbol = Column(String(20), nullable=True)
    cost_basis = Column(Numeric(12, 2), nullable=True)
    is_bunched = Column(Boolean, default=False, nullable=False)
    tax_year = Column(Integer, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User")
    account = relationship("Account")

    def __repr__(self):
        return f"<CharitableDonation {self.organization_name!r} amount={self.amount} year={self.tax_year}>"
