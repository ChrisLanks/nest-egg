"""Account schemas."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel

from app.models.account import (
    AccountType,
    AccountSource,
    PropertyType,
    GrantType,
    CompanyStatus,
    ValuationMethod,
    CompoundingFrequency,
)


class AccountBase(BaseModel):
    """Base account schema."""

    name: str
    account_type: AccountType
    property_type: Optional[PropertyType] = None  # For PROPERTY accounts only
    account_source: AccountSource
    institution_name: Optional[str] = None
    mask: Optional[str] = None


class AccountCreate(AccountBase):
    """Account creation schema."""

    pass


class HoldingData(BaseModel):
    """Holding data for account creation."""

    ticker: str
    shares: Decimal
    price_per_share: Decimal


class ManualAccountCreate(BaseModel):
    """Manual account creation schema."""

    name: str
    account_type: AccountType
    property_type: Optional[PropertyType] = None  # For PROPERTY accounts only
    account_source: AccountSource
    institution: Optional[str] = None
    balance: Decimal
    account_number_last4: Optional[str] = None
    holdings: Optional[List[HoldingData]] = None  # For investment accounts

    # Debt/Loan fields
    interest_rate: Optional[Decimal] = None
    interest_rate_type: Optional[str] = None  # 'FIXED' or 'VARIABLE'
    minimum_payment: Optional[Decimal] = None
    payment_due_day: Optional[int] = None
    original_amount: Optional[Decimal] = None
    origination_date: Optional[date] = None
    maturity_date: Optional[date] = None
    loan_term_months: Optional[int] = None
    compounding_frequency: Optional[CompoundingFrequency] = None  # For CD accounts

    # Private Debt fields
    principal_amount: Optional[Decimal] = None

    # Private Equity fields
    grant_type: Optional[GrantType] = None
    grant_date: Optional[date] = None
    quantity: Optional[Decimal] = None  # Number of shares/options
    strike_price: Optional[Decimal] = None  # Exercise price
    vesting_schedule: Optional[str] = None  # JSON array: [{"date": "2024-01-01", "quantity": 250}]
    share_price: Optional[Decimal] = None  # Current estimated price per share
    company_status: Optional[CompanyStatus] = None
    valuation_method: Optional[ValuationMethod] = None
    include_in_networth: Optional[bool] = None  # None = auto (public=true, private=false)

    # Pension / Annuity income fields
    monthly_benefit: Optional[Decimal] = None   # Monthly income amount
    benefit_start_date: Optional[date] = None   # When payments begin

    # Credit card fields
    credit_limit: Optional[Decimal] = None      # Credit limit (stored as `limit` on Account)

    # Business Equity fields
    company_valuation: Optional[Decimal] = None  # Total company valuation
    ownership_percentage: Optional[Decimal] = None  # Percentage ownership (0-100)
    equity_value: Optional[Decimal] = None  # Direct equity value

    # Property auto-valuation fields
    property_address: Optional[str] = None
    property_zip: Optional[str] = None

    # Vehicle auto-valuation fields
    vehicle_vin: Optional[str] = None
    vehicle_mileage: Optional[int] = None


class AccountUpdate(BaseModel):
    """Account update schema."""

    name: Optional[str] = None
    is_active: Optional[bool] = None
    current_balance: Optional[Decimal] = None
    mask: Optional[str] = None
    exclude_from_cash_flow: Optional[bool] = None

    # Debt/Loan fields
    interest_rate: Optional[Decimal] = None
    interest_rate_type: Optional[str] = None
    minimum_payment: Optional[Decimal] = None
    payment_due_day: Optional[int] = None
    original_amount: Optional[Decimal] = None
    origination_date: Optional[date] = None
    maturity_date: Optional[date] = None
    loan_term_months: Optional[int] = None
    compounding_frequency: Optional[CompoundingFrequency] = None  # For CD accounts

    # Private Debt fields
    principal_amount: Optional[Decimal] = None

    # Private Equity fields
    grant_type: Optional[GrantType] = None
    grant_date: Optional[date] = None
    quantity: Optional[Decimal] = None
    strike_price: Optional[Decimal] = None
    vesting_schedule: Optional[str] = None
    share_price: Optional[Decimal] = None
    company_status: Optional[CompanyStatus] = None
    valuation_method: Optional[ValuationMethod] = None
    include_in_networth: Optional[bool] = None

    # Pension / Annuity income fields
    monthly_benefit: Optional[Decimal] = None
    benefit_start_date: Optional[date] = None

    # Credit card fields
    credit_limit: Optional[Decimal] = None

    # Business Equity fields
    company_valuation: Optional[Decimal] = None
    ownership_percentage: Optional[Decimal] = None
    equity_value: Optional[Decimal] = None

    # Property auto-valuation
    property_address: Optional[str] = None
    property_zip: Optional[str] = None

    # Vehicle auto-valuation
    vehicle_vin: Optional[str] = None
    vehicle_mileage: Optional[int] = None


class Account(AccountBase):
    """Account response schema."""

    id: UUID
    organization_id: UUID
    user_id: UUID
    property_type: Optional[PropertyType] = None  # For PROPERTY accounts only
    external_account_id: Optional[str] = None
    plaid_item_hash: Optional[str] = None  # For duplicate detection across users
    current_balance: Optional[Decimal] = None
    available_balance: Optional[Decimal] = None
    limit: Optional[Decimal] = None
    balance_as_of: Optional[datetime] = None
    is_active: bool
    is_manual: bool
    exclude_from_cash_flow: bool
    created_at: datetime
    updated_at: datetime

    # Debt/Loan fields
    interest_rate: Optional[Decimal] = None
    interest_rate_type: Optional[str] = None
    minimum_payment: Optional[Decimal] = None
    payment_due_day: Optional[int] = None
    original_amount: Optional[Decimal] = None
    origination_date: Optional[date] = None
    maturity_date: Optional[date] = None
    loan_term_months: Optional[int] = None
    compounding_frequency: Optional[CompoundingFrequency] = None  # For CD accounts

    # Private Debt fields
    principal_amount: Optional[Decimal] = None

    # Private Equity fields
    grant_type: Optional[GrantType] = None
    grant_date: Optional[date] = None
    quantity: Optional[Decimal] = None
    strike_price: Optional[Decimal] = None
    vesting_schedule: Optional[str] = None
    share_price: Optional[Decimal] = None
    company_status: Optional[CompanyStatus] = None
    valuation_method: Optional[ValuationMethod] = None
    include_in_networth: Optional[bool] = None

    # Pension / Annuity income fields
    monthly_benefit: Optional[Decimal] = None
    benefit_start_date: Optional[date] = None

    # Business Equity fields
    company_valuation: Optional[Decimal] = None
    ownership_percentage: Optional[Decimal] = None
    equity_value: Optional[Decimal] = None

    # Property auto-valuation
    property_address: Optional[str] = None
    property_zip: Optional[str] = None

    # Vehicle auto-valuation
    vehicle_vin: Optional[str] = None
    vehicle_mileage: Optional[int] = None

    # Auto-valuation metadata
    last_auto_valued_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AccountSummary(BaseModel):
    """Account summary for lists (provider-agnostic)."""

    id: UUID
    user_id: UUID
    name: str
    account_type: AccountType
    account_source: AccountSource  # plaid, teller, mx, manual
    property_type: Optional[PropertyType] = None  # For PROPERTY accounts only
    institution_name: Optional[str] = None
    mask: Optional[str] = None
    current_balance: Optional[Decimal] = None
    balance_as_of: Optional[datetime] = None
    is_active: bool
    exclude_from_cash_flow: bool
    plaid_item_hash: Optional[str] = None  # For duplicate detection

    # Provider-agnostic sync status (populated from PlaidItem, TellerEnrollment, etc.)
    provider_item_id: Optional[UUID] = None  # ID of PlaidItem or TellerEnrollment
    last_synced_at: Optional[datetime] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    needs_reauth: Optional[bool] = None
