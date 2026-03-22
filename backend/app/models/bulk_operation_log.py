"""Bulk operation log model for undo/redo support."""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class BulkOperationLog(Base):
    """Audit log for bulk operations, enabling undo functionality."""

    __tablename__ = "bulk_operation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_type = Column(String(50), nullable=False)  # "categorize", "merge", "delete", "split"
    affected_ids = Column(JSON, nullable=False)  # list of transaction/account IDs
    previous_state = Column(JSON, nullable=False)  # snapshot before change
    new_state = Column(JSON, nullable=True)  # snapshot after change
    is_undone = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    undone_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User")

    def __repr__(self):
        return f"<BulkOperationLog {self.operation_type} by user {self.user_id}>"
