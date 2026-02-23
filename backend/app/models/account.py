"""Account and Plaid item models."""

import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    Text,
    Integer,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.services.encryption_service import EncryptedString
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


class GrantType(str, enum.Enum):
    """Grant type for private equity/stock options."""

    ISO = "iso"  # Incentive Stock Option
    NSO = "nso"  # Non-Qualified Stock Option
    RSU = "rsu"  # Restricted Stock Unit
    RSA = "rsa"  # Restricted Stock Award
    PROFIT_INTEREST = "profit_interest"  # LLC Profits Interest (membership units)


class CompanyStatus(str, enum.Enum):
    """Company status for private equity."""

    PRIVATE = "private"
    PUBLIC = "public"


class ValuationMethod(str, enum.Enum):
    """Valuation method for private equity."""

    FMV_409A = "409a"  # Fair Market Value (409A valuation)
    PREFERRED_PRICE = "preferred"  # Last round preferred price
    CUSTOM_PRICE = "custom"  # Custom price


class CompoundingFrequency(str, enum.Enum):
    """Compounding frequency for CDs and interest-bearing accounts."""

    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    AT_MATURITY = "at_maturity"  # Simple interest paid at maturity


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
    PRIVATE_DEBT = "private_debt"  # Private credit funds or loans you've made
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
    TELLER = "teller"
    MX = "mx"
    MANUAL = "manual"


class TellerEnrollment(Base):
    """Teller Enrollment represents a connected financial institution."""

    __tablename__ = "teller_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Teller identifiers
    enrollment_id = Column(String(255), unique=True, nullable=False, index=True)
    access_token = Column(Text, nullable=False)  # Encrypted

    # Institution info
    institution_name = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Sync state
    last_synced_at = Column(DateTime, nullable=True)

    # Error tracking
    last_error_code = Column(String(100), nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    accounts = relationship(
        "Account", back_populates="teller_enrollment", cascade="all, delete-orphan"
    )

    def get_decrypted_access_token(self) -> str:
        """Get the decrypted access token."""
        from app.services.encryption_service import get_encryption_service

        encryption_service = get_encryption_service()
        return encryption_service.decrypt_token(self.access_token)


class PlaidItem(Base):
    """Plaid Item represents a set of credentials at a financial institution."""

    __tablename__ = "plaid_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

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

    def get_decrypted_access_token(self) -> str:
        """
        Get the decrypted access token.

        Returns:
            Decrypted access token string
        """
        from app.services.encryption_service import get_encryption_service

        encryption_service = get_encryption_service()
        return encryption_service.decrypt_token(self.access_token)

    def set_encrypted_access_token(self, plaintext_token: str) -> None:
        """
        Set the access token (will be encrypted).

        Args:
            plaintext_token: The plaintext token to encrypt and store
        """
        from app.services.encryption_service import get_encryption_service

        encryption_service = get_encryption_service()
        self.access_token = encryption_service.encrypt_token(plaintext_token)


class Account(Base):
    """Financial account (bank, credit card, investment, etc.)."""

    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plaid_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plaid_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    teller_enrollment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teller_enrollments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Account identification
    name = Column(String(255), nullable=False)
    account_type = Column(SQLEnum(AccountType), nullable=False, index=True)
    property_type = Column(SQLEnum(PropertyType), nullable=True)  # Only for PROPERTY accounts
    account_source = Column(SQLEnum(AccountSource), default=AccountSource.PLAID, nullable=False)

    # External identifiers
    external_account_id = Column(String(255), nullable=True, index=True)  # Plaid account_id
    mask = Column(String(10), nullable=True)  # Last 4 digits
    plaid_item_hash = Column(
        String(64), nullable=True, index=True
    )  # SHA256 hash for duplicate detection

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
    exclude_from_cash_flow = Column(
        Boolean, default=False, nullable=False
    )  # Exclude transactions from budgets/trends to prevent double-counting

    # Debt/Loan fields (for debt payoff planning)
    interest_rate = Column(Numeric(5, 2), nullable=True)  # Annual interest rate (APR) as percentage
    interest_rate_type = Column(String(20), nullable=True)  # 'FIXED' or 'VARIABLE'
    minimum_payment = Column(Numeric(10, 2), nullable=True)  # Minimum monthly payment
    payment_due_day = Column(Integer, nullable=True)  # Day of month payment is due
    original_amount = Column(Numeric(15, 2), nullable=True)  # Original loan/debt amount
    origination_date = Column(Date, nullable=True)  # Date loan was originated
    maturity_date = Column(Date, nullable=True)  # Date loan matures/ends
    loan_term_months = Column(Integer, nullable=True)  # Total loan term in months
    compounding_frequency = Column(SQLEnum(CompoundingFrequency), nullable=True)  # How interest compounds (for CDs)

    # Private Debt fields (for private credit funds or loans made)
    principal_amount = Column(Numeric(15, 2), nullable=True)  # Original principal amount

    # Private Equity fields (for RSUs, stock options, company equity)
    grant_type = Column(SQLEnum(GrantType), nullable=True)  # ISO, NSO, RSU, RSA
    grant_date = Column(Date, nullable=True)  # Date equity was granted
    quantity = Column(Numeric(15, 4), nullable=True)  # Number of shares/options
    strike_price = Column(Numeric(15, 4), nullable=True)  # Exercise price (for options)
    vesting_schedule = Column(Text, nullable=True)  # JSON: [{"date": "2024-01-01", "quantity": 250, "notes": ""}]
    share_price = Column(Numeric(15, 4), nullable=True)  # Current estimated price per share
    company_status = Column(SQLEnum(CompanyStatus), nullable=True)  # Private or Public
    valuation_method = Column(SQLEnum(ValuationMethod), nullable=True)  # 409a, Preferred, Custom
    include_in_networth = Column(Boolean, default=None, nullable=True)  # None = auto (public=true, private=false)

    # Pension / Annuity income fields
    monthly_benefit = Column(Numeric(10, 2), nullable=True)   # Monthly income when in payout phase
    benefit_start_date = Column(Date, nullable=True)           # Date payments begin

    # Business Equity fields (for business ownership)
    company_valuation = Column(Numeric(15, 2), nullable=True)  # Total company valuation
    ownership_percentage = Column(Numeric(5, 2), nullable=True)  # Percentage ownership (0-100)
    equity_value = Column(Numeric(15, 2), nullable=True)  # Direct equity value (alternative to valuation + percentage)

    # Employer 401k / 403b match fields
    employer_match_percent = Column(Numeric(5, 2), nullable=True)   # e.g. 50 → employer matches 50% of contribution
    employer_match_limit_percent = Column(Numeric(5, 2), nullable=True)  # e.g. 6 → on the first 6% of salary
    annual_salary = Column(EncryptedString, nullable=True)          # Encrypted — decrypt to Decimal for arithmetic

    # Interest accrual tracking (CD / savings / money_market)
    last_interest_accrued_at = Column(Date, nullable=True)          # Date of last auto-accrual (prevents double-accrual)

    # Property auto-valuation fields (used with ATTOM API)
    # Stored encrypted — EncryptedString transparently encrypts on write, decrypts on read.
    property_address = Column(EncryptedString, nullable=True)   # Street address (e.g. "123 Main St")
    property_zip = Column(EncryptedString, nullable=True)       # ZIP / postal code

    # Vehicle auto-valuation fields (used with MarketCheck API + NHTSA VIN decode)
    vehicle_vin = Column(EncryptedString, nullable=True)        # VIN for auto-decode + valuation
    vehicle_mileage = Column(Integer, nullable=True)        # Current odometer for market value

    # Auto-valuation metadata (property + vehicle)
    last_auto_valued_at = Column(DateTime, nullable=True)   # When balance was last set by the API

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    plaid_item = relationship("PlaidItem", back_populates="accounts")
    teller_enrollment = relationship("TellerEnrollment", back_populates="accounts")
    transactions = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    holdings = relationship("Holding", back_populates="account", cascade="all, delete-orphan")
