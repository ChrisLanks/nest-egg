"""Transaction merge tracking models."""

import uuid

from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class TransactionMerge(Base):
    """Tracks merged transactions to prevent duplicate entries and maintain audit trail."""

    __tablename__ = "transaction_merges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Primary transaction (the one that was kept)
    primary_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Duplicate transaction (the one that was merged/deleted)
    duplicate_transaction_id = Column(
        UUID(as_uuid=True), nullable=False, index=True
    )  # No FK since it's deleted

    # Merge metadata
    merge_reason = Column(Text, nullable=True)  # User note or auto-detection reason
    is_auto_merged = Column(Boolean, default=False, nullable=False)  # Auto vs manual merge

    # Timestamps
    merged_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    merged_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    primary_transaction = relationship("Transaction")
    merged_by = relationship("User")

    __table_args__ = (
        Index("ix_transaction_merges_primary", "primary_transaction_id"),
        Index("ix_transaction_merges_duplicate", "duplicate_transaction_id"),
        Index("ix_transaction_merges_org_date", "organization_id", "merged_at"),
    )
