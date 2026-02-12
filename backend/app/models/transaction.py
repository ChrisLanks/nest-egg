"""Transaction models."""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Transaction(Base):
    """Financial transaction."""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    # External identifier (from Plaid/MX)
    external_transaction_id = Column(String(255), nullable=True, index=True)

    # Transaction details
    date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)  # Positive for income, negative for expenses
    merchant_name = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)

    # Categorization
    category_primary = Column(String(100), nullable=True)  # From Plaid
    category_detailed = Column(String(100), nullable=True)  # From Plaid

    # Status
    is_pending = Column(Boolean, default=False, nullable=False, index=True)

    # Deduplication
    deduplication_hash = Column(String(64), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    labels = relationship("TransactionLabel", back_populates="transaction", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('ix_transactions_org_date', 'organization_id', 'date'),
        Index('ix_transactions_account_date', 'account_id', 'date'),
        Index('ix_transactions_dedup', 'account_id', 'deduplication_hash', unique=True),
    )


class Label(Base):
    """Custom transaction labels/categories."""

    __tablename__ = "labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Label details
    name = Column(String(100), nullable=False)
    color = Column(String(7), nullable=True)  # Hex color code
    parent_label_id = Column(UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), nullable=True)

    # Type flags
    is_income = Column(Boolean, default=False, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # System-created labels

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transactions = relationship("TransactionLabel", back_populates="label", cascade="all, delete-orphan")
    parent = relationship("Label", remote_side=[id], backref="children")

    __table_args__ = (
        Index('ix_labels_org_name', 'organization_id', 'name', unique=True),
    )


class TransactionLabel(Base):
    """Many-to-many relationship between transactions and labels."""

    __tablename__ = "transaction_labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    label_id = Column(UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), nullable=False, index=True)

    # Track which rule applied this label (if any)
    applied_by_rule_id = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="labels")
    label = relationship("Label", back_populates="transactions")

    __table_args__ = (
        Index('ix_transaction_labels_unique', 'transaction_id', 'label_id', unique=True),
    )
