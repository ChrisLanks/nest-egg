"""Persistent audit log model for SOC 2 compliance.

Stores tamper-evident records of sensitive API operations in the database,
complementing the application-level log entries from AuditLogMiddleware.
"""

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class AuditLog(Base):
    """Persistent audit log entry for SOC 2 compliance.

    Records are append-only — no UPDATE or DELETE operations should be
    performed on this table.  Retention policies should be enforced via
    a scheduled job that archives old rows, not by deletion.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    status_code = Column(Integer, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # Stored redacted
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False, index=True)
    detail = Column(Text, nullable=True)  # Optional extra context

    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )
