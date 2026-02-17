"""Rule models for automated transaction categorization."""

import uuid
from typing import Optional
import enum

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class RuleMatchType(str, enum.Enum):
    """How multiple conditions should be evaluated."""
    ALL = "all"  # All conditions must match (AND)
    ANY = "any"  # Any condition can match (OR)


class RuleApplyTo(str, enum.Enum):
    """Which transactions should the rule apply to."""
    NEW_ONLY = "new_only"  # Only future transactions
    EXISTING_ONLY = "existing_only"  # Only past transactions
    BOTH = "both"  # All transactions
    SINGLE = "single"  # Single transaction (one-time application)


class ConditionField(str, enum.Enum):
    """Fields that can be matched in conditions."""
    MERCHANT_NAME = "merchant_name"
    AMOUNT = "amount"
    AMOUNT_EXACT = "amount_exact"
    CATEGORY = "category"
    DESCRIPTION = "description"
    # Date-based conditions
    DATE = "date"  # Specific date or date range
    MONTH = "month"  # Month number (1-12)
    YEAR = "year"  # Year (2024, 2025, etc.)
    DAY_OF_WEEK = "day_of_week"  # Day of week (0=Monday, 6=Sunday)
    # Account-based conditions
    ACCOUNT_ID = "account_id"  # Specific account
    ACCOUNT_TYPE = "account_type"  # Account type (checking, savings, credit_card, etc.)


class ConditionOperator(str, enum.Enum):
    """Operators for condition matching."""
    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"
    REGEX = "regex"


class ActionType(str, enum.Enum):
    """Types of actions that can be performed."""
    SET_CATEGORY = "set_category"
    ADD_LABEL = "add_label"
    REMOVE_LABEL = "remove_label"
    SET_MERCHANT = "set_merchant"


class Rule(Base):
    """Automated rule for transaction categorization."""

    __tablename__ = "rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Rule metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=0, nullable=False)  # Higher priority runs first

    # Match configuration
    match_type = Column(SQLEnum(RuleMatchType), default=RuleMatchType.ALL, nullable=False)
    apply_to = Column(SQLEnum(RuleApplyTo), default=RuleApplyTo.NEW_ONLY, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Statistics
    times_applied = Column(Integer, default=0, nullable=False)
    last_applied_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    conditions = relationship("RuleCondition", back_populates="rule", cascade="all, delete-orphan")
    actions = relationship("RuleAction", back_populates="rule", cascade="all, delete-orphan")


class RuleCondition(Base):
    """Condition that must be met for a rule to apply."""

    __tablename__ = "rule_conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)

    # Condition configuration
    field = Column(SQLEnum(ConditionField), nullable=False)
    operator = Column(SQLEnum(ConditionOperator), nullable=False)
    value = Column(Text, nullable=False)  # Can store JSON for complex values

    # For BETWEEN operator
    value_max = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    # Relationships
    rule = relationship("Rule", back_populates="conditions")


class RuleAction(Base):
    """Action to perform when a rule matches."""

    __tablename__ = "rule_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)

    # Action configuration
    action_type = Column(SQLEnum(ActionType), nullable=False)
    action_value = Column(Text, nullable=False)  # Label ID, category name, etc.

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    # Relationships
    rule = relationship("Rule", back_populates="actions")
