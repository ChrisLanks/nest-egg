"""Transaction attachment models."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class TransactionAttachment(Base):
    """File attachment (receipt, document) linked to a transaction."""

    __tablename__ = "transaction_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File metadata
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False)  # path in S3 or local
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)

    # OCR extraction results (best-effort, never blocks upload)
    ocr_status = Column(String(20), nullable=True)  # "pending", "completed", "failed", "skipped"
    ocr_data = Column(JSON, nullable=True)  # extracted: {merchant, amount, date, raw_text}

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    # Relationships
    transaction = relationship("Transaction", backref="attachments")

    __table_args__ = (
        Index("ix_transaction_attachments_txn_id", "transaction_id"),
        Index("ix_transaction_attachments_org_id", "organization_id"),
    )
