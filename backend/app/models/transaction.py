"""Transaction models."""

import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class Transaction(Base):
    """Financial transaction."""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External identifier (from Plaid/MX)
    external_transaction_id = Column(String(255), nullable=True, index=True)

    # Transaction details
    date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)  # Positive for income, negative for expenses
    merchant_name = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)

    # Categorization
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # Custom category
    category_primary = Column(String(100), nullable=True)  # From account provider (Plaid, Teller, MX)
    category_detailed = Column(String(100), nullable=True)  # Detailed category from provider

    # Status
    is_pending = Column(Boolean, default=False, nullable=False, index=True)
    is_transfer = Column(
        Boolean, default=False, nullable=False, index=True
    )  # Exclude from cash flow to prevent double-counting

    # Deduplication
    deduplication_hash = Column(String(64), nullable=False, index=True)

    # Splitting
    is_split = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    labels = relationship(
        "TransactionLabel", back_populates="transaction", cascade="all, delete-orphan"
    )
    splits = relationship(
        "TransactionSplit", back_populates="parent_transaction", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_transactions_org_date", "organization_id", "date"),
        Index("ix_transactions_account_date", "account_id", "date"),
        Index("ix_transactions_dedup", "account_id", "deduplication_hash", unique=True),
        Index("ix_transactions_org_category", "organization_id", "category_primary"),
    )


class Category(Base):
    """Custom transaction categories with hierarchy support."""

    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Category details
    name = Column(String(100), nullable=False)
    color = Column(String(7), nullable=True)  # Hex color code
    parent_category_id = Column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True
    )

    # Link to provider category for automatic mapping
    plaid_category_name = Column(
        String(100), nullable=True, index=True
    )  # Original provider category_primary (field name kept for backward compatibility)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")

    __table_args__ = (Index("ix_categories_org_name", "organization_id", "name", unique=True),)


class Label(Base):
    """Custom transaction labels (tags)."""

    __tablename__ = "labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Label details
    name = Column(String(100), nullable=False)
    color = Column(String(7), nullable=True)  # Hex color code

    # Hierarchy (optional parent label for grouping)
    parent_label_id = Column(
        UUID(as_uuid=True),
        ForeignKey("labels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Type flags
    is_income = Column(Boolean, default=False, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # System-created labels

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    transactions = relationship(
        "TransactionLabel", back_populates="label", cascade="all, delete-orphan"
    )
    children = relationship("Label", backref=backref("parent", remote_side="Label.id"), lazy="select")

    __table_args__ = (Index("ix_labels_org_name", "organization_id", "name", unique=True),)


class TransactionLabel(Base):
    """Many-to-many relationship between transactions and labels."""

    __tablename__ = "transaction_labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label_id = Column(
        UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Track which rule applied this label (if any)
    applied_by_rule_id = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="labels")
    label = relationship("Label", back_populates="transactions")

    __table_args__ = (
        Index("ix_transaction_labels_unique", "transaction_id", "label_id", unique=True),
    )


class TransactionSplit(Base):
    """Transaction splits for dividing a transaction into multiple categories."""

    __tablename__ = "transaction_splits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Split details
    amount = Column(Numeric(15, 2), nullable=False)  # Portion of parent amount
    description = Column(Text, nullable=True)
    category_id = Column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    parent_transaction = relationship("Transaction", back_populates="splits")
    category = relationship("Category")


# Export the table for use in queries (many-to-many joins)
transaction_labels = TransactionLabel.__table__
