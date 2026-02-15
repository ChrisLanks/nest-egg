"""Account and Plaid item models."""

import uuid
from typing import Optional
import enum

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class AccountCategory(str, enum.Enum):
    """Financial category classification for account types."""
    ASSET = "asset"
    DEBT = "debt"


class PropertyType(str, enum.Enum):
    """Property classification for real estate accounts."""
    PERSONAL_RESIDENCE = "personal_residence"
    INVESTMENT = "investment"
    VACATION_HOME = "vacation_home"


class AccountType(str, enum.Enum):
    """Account types with automatic asset/debt classification."""
    # Cash & Checking
    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money_market"
    CD = "cd"

    # Credit & Debt
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    STUDENT_LOAN = "student_loan"
    MORTGAGE = "mortgage"

    # Investment Accounts
    BROKERAGE = "brokerage"
    RETIREMENT_401K = "retirement_401k"
    RETIREMENT_IRA = "retirement_ira"
    RETIREMENT_ROTH = "retirement_roth"
    RETIREMENT_529 = "retirement_529"
    HSA = "hsa"
    PENSION = "pension"

    # Alternative Investments
    CRYPTO = "crypto"
    PRIVATE_EQUITY = "private_equity"
    COLLECTIBLES = "collectibles"
    PRECIOUS_METALS = "precious_metals"

    # Real Estate & Vehicles
    PROPERTY = "property"
    VEHICLE = "vehicle"

    # Insurance & Annuities
    LIFE_INSURANCE_CASH_VALUE = "life_insurance_cash_value"
    ANNUITY = "annuity"

    # Securities
    BOND = "bond"
    STOCK_OPTIONS = "stock_options"

    # Business
    BUSINESS_EQUITY = "business_equity"

    # Other
    MANUAL = "manual"
    OTHER = "other"

    @property
    def category(self) -> AccountCategory:
        """Get the financial category (asset or debt) for this account type."""
        debt_types = {
            AccountType.CREDIT_CARD,
            AccountType.LOAN,
            AccountType.STUDENT_LOAN,
            AccountType.MORTGAGE,
        }
        return AccountCategory.DEBT if self in debt_types else AccountCategory.ASSET

    @property
    def is_asset(self) -> bool:
        """Check if this account type is an asset."""
        return self.category == AccountCategory.ASSET

    @property
    def is_debt(self) -> bool:
        """Check if this account type is a debt."""
        return self.category == AccountCategory.DEBT


class AccountSource(str, enum.Enum):
    """Account data sources."""
    PLAID = "plaid"
    MX = "mx"
    MANUAL = "manual"


class PlaidItem(Base):
    """Plaid Item represents a set of credentials at a financial institution."""

    __tablename__ = "plaid_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Plaid identifiers
    item_id = Column(String(255), unique=True, nullable=False, index=True)
    access_token = Column(Text, nullable=False)  # Encrypted

    # Institution info
    institution_id = Column(String(255), nullable=True)
    institution_name = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    needs_reauth = Column(Boolean, default=False, nullable=False)

    # Sync state
    cursor = Column(Text, nullable=True)  # For incremental transaction sync
    last_synced_at = Column(DateTime, nullable=True)

    # Error tracking
    last_error_code = Column(String(100), nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    accounts = relationship("Account", back_populates="plaid_item", cascade="all, delete-orphan")


class Account(Base):
    """Financial account (bank, credit card, investment, etc.)."""

    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plaid_item_id = Column(UUID(as_uuid=True), ForeignKey("plaid_items.id", ondelete="CASCADE"), nullable=True, index=True)

    # Account identification
    name = Column(String(255), nullable=False)
    account_type = Column(SQLEnum(AccountType), nullable=False, index=True)
    property_type = Column(SQLEnum(PropertyType), nullable=True)  # Only for PROPERTY accounts
    account_source = Column(SQLEnum(AccountSource), default=AccountSource.PLAID, nullable=False)

    # External identifiers
    external_account_id = Column(String(255), nullable=True, index=True)  # Plaid account_id
    mask = Column(String(10), nullable=True)  # Last 4 digits
    plaid_item_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash for duplicate detection

    # Institution
    institution_name = Column(String(255), nullable=True)

    # Balance tracking
    current_balance = Column(Numeric(15, 2), nullable=True)
    available_balance = Column(Numeric(15, 2), nullable=True)
    limit = Column(Numeric(15, 2), nullable=True)  # Credit limit for credit cards

    # Balance timestamps
    balance_as_of = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_manual = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    plaid_item = relationship("PlaidItem", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    holdings = relationship("Holding", back_populates="account", cascade="all, delete-orphan")
