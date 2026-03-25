"""Estate document model for tracking legal estate planning documents."""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class EstateDocument(Base):
    """
    Estate document record for tracking whether key legal documents exist
    and when they were last reviewed.

    Document types: will / trust / poa / healthcare_directive / beneficiary_form
    """

    __tablename__ = "estate_documents"

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

    # will / trust / poa / healthcare_directive / beneficiary_form
    document_type = Column(String(50), nullable=False)
    last_reviewed_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now_lambda, nullable=False)

    def __repr__(self):
        return (
            f"<EstateDocument {self.document_type} user={self.user_id} "
            f"reviewed={self.last_reviewed_date}>"
        )
