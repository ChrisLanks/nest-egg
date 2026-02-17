"""Multi-Factor Authentication models."""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda
from uuid import uuid4


class UserMFA(Base):
    """User MFA configuration."""

    __tablename__ = "user_mfa"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # TOTP secret (encrypted)
    secret = Column(String(255), nullable=False)

    # MFA status
    is_enabled = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Backup codes (encrypted, comma-separated)
    backup_codes = Column(Text, nullable=True)

    # Timestamps
    enabled_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    user = relationship("User", back_populates="mfa")
