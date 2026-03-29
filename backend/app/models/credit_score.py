"""Credit score model for manual credit score tracking."""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class CreditScore(Base):
    """Manually-entered credit score snapshot.

    Users enter scores they pull from Equifax, TransUnion, Experian, FICO,
    or their bank's credit monitoring tool. Stored as a time series so trends
    can be charted on the Financial Health page.
    """

    __tablename__ = "credit_scores"

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

    score = Column(Integer, nullable=False)  # 300–850
    score_date = Column(Date, nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # Equifax / TransUnion / Experian / FICO / Other
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<CreditScore {self.score} ({self.provider}) on {self.score_date}>"
