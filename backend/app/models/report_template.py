"""Report template models."""

import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class ReportTemplate(Base):
    """Saved report template for custom financial reports."""

    __tablename__ = "report_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Template details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=False)  # 'income_expense', 'cash_flow', etc.

    # Report configuration (stored as JSON)
    config = Column(JSONB, nullable=False)
    """
    Config JSON structure:
    {
        "dateRange": {
            "type": "preset" | "custom",
            "preset": "last_30_days" | "last_90_days" | "this_month" | "this_year" | "last_year",
            "startDate": "2024-01-01",  # For custom
            "endDate": "2024-12-31"  # For custom
        },
        "groupBy": "category" | "label" | "merchant" | "account" | "time",
        "timeGrouping": "daily" | "weekly" | "monthly" | "quarterly" | "yearly",  # When groupBy="time"
        "filters": {
            "labelIds": ["uuid1", "uuid2"],
            "categoryIds": ["uuid1", "uuid2"],
            "accountIds": ["uuid1", "uuid2"],
            "minAmount": 100.00,
            "maxAmount": 1000.00,
            "transactionType": "income" | "expense" | "both"
        },
        "chartType": "bar" | "line" | "pie" | "table" | "area",
        "metrics": ["sum", "average", "count"],
        "sortBy": "amount" | "count" | "name",
        "sortDirection": "asc" | "desc",
        "limit": 10  # Top N results
    }
    """

    # Sharing
    is_shared = Column(Boolean, default=False, nullable=False)  # Shared with household

    # Metadata
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime, nullable=False, default=utc_now_lambda)
    updated_at = Column(DateTime, nullable=False, default=utc_now_lambda, onupdate=utc_now_lambda)

    # Relationships
    organization = relationship("Organization", back_populates="report_templates")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
