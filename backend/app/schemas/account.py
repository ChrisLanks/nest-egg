"""Account schemas."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

# Numeric bounds — prevents absurd values that would cause DB errors (Numeric 15,2)
# or display issues. These cover any realistic personal-finance scenario.
_MAX_BALANCE = Decimal("999999999999.99")  # ~$1 trillion
_MAX_RATE = Decimal("200.00")  # 200% APR — covers worst-case payday loans
_MAX_PAYMENT = Decimal("999999999.99")
_MAX_PRICE = Decimal("999999999.99")
_MAX_SALARY = Decimal("999999999.99")
_MAX_MATCH_PCT = Decimal("100.00")

from app.models.account import (
    AccountType,
    AccountSource,
    PropertyType,
    GrantType,
    CompanyStatus,
    ValuationMethod,
    CompoundingFrequency,
    TaxTreatment,
)


class VestingMilestone(BaseModel):
    """A single vesting event: date + quantity."""

    date: date
    quantity: Decimal = Field(ge=0)


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
    balance: Decimal = Field(ge=-_MAX_BALANCE, le=_MAX_BALANCE)
    account_number_last4: Optional[str] = None
    holdings: Optional[List[HoldingData]] = None  # For investment accounts

    # Debt/Loan fields
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=_MAX_RATE)
    interest_rate_type: Optional[str] = None  # 'FIXED' or 'VARIABLE'
    minimum_payment: Optional[Decimal] = Field(None, ge=0, le=_MAX_PAYMENT)
    payment_due_day: Optional[int] = None
    original_amount: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)
    origination_date: Optional[date] = None
    maturity_date: Optional[date] = None
    loan_term_months: Optional[int] = None
    compounding_frequency: Optional[CompoundingFrequency] = None  # For CD accounts

    # Private Debt fields
    principal_amount: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)

    # Private Equity fields
    grant_type: Optional[GrantType] = None
    grant_date: Optional[date] = None
    quantity: Optional[Decimal] = Field(None, ge=0)  # Number of shares/options
    strike_price: Optional[Decimal] = Field(None, ge=0, le=_MAX_PRICE)  # Exercise price
    vesting_schedule: Optional[List[VestingMilestone]] = (
        None  # Validated; serialized to JSON for storage
    )
    share_price: Optional[Decimal] = Field(None, ge=0, le=_MAX_PRICE)  # Current estimated price per share
    company_status: Optional[CompanyStatus] = None
    valuation_method: Optional[ValuationMethod] = None
    include_in_networth: Optional[bool] = None  # None = auto (public=true, private=false)

    # Pension / Annuity income fields
    monthly_benefit: Optional[Decimal] = Field(None, ge=0, le=_MAX_PAYMENT)  # Monthly income amount
    benefit_start_date: Optional[date] = None  # When payments begin

    # Credit card fields
    credit_limit: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)  # Credit limit (stored as `limit` on Account)

    # Business Equity fields
    company_valuation: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)  # Total company valuation
    ownership_percentage: Optional[Decimal] = Field(
        None, ge=0, le=100
    )  # Percentage ownership (0-100)
    equity_value: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)  # Direct equity value

    # Tax treatment (retirement accounts)
    tax_treatment: Optional[TaxTreatment] = None

    # Employer match fields (401k / 403b)
    employer_match_percent: Optional[Decimal] = Field(None, ge=0, le=_MAX_MATCH_PCT)
    employer_match_limit_percent: Optional[Decimal] = Field(None, ge=0, le=_MAX_MATCH_PCT)
    annual_salary: Optional[Decimal] = Field(None, ge=0, le=_MAX_SALARY)

    # Property auto-valuation fields
    property_address: Optional[str] = None
    property_zip: Optional[str] = None

    # Vehicle auto-valuation fields
    vehicle_vin: Optional[str] = None
    vehicle_mileage: Optional[int] = None

    # Valuation adjustment (property + vehicle)
    valuation_adjustment_pct: Optional[Decimal] = None


class AccountUpdate(BaseModel):
    """Account update schema."""

    name: Optional[str] = None
    is_active: Optional[bool] = None
    current_balance: Optional[Decimal] = Field(None, ge=-_MAX_BALANCE, le=_MAX_BALANCE)
    mask: Optional[str] = None
    exclude_from_cash_flow: Optional[bool] = None

    # Debt/Loan fields
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=_MAX_RATE)
    interest_rate_type: Optional[str] = None
    minimum_payment: Optional[Decimal] = Field(None, ge=0, le=_MAX_PAYMENT)
    payment_due_day: Optional[int] = None
    original_amount: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)
    origination_date: Optional[date] = None
    maturity_date: Optional[date] = None
    loan_term_months: Optional[int] = None
    compounding_frequency: Optional[CompoundingFrequency] = None  # For CD accounts

    # Private Debt fields
    principal_amount: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)

    # Private Equity fields
    grant_type: Optional[GrantType] = None
    grant_date: Optional[date] = None
    quantity: Optional[Decimal] = Field(None, ge=0)
    strike_price: Optional[Decimal] = Field(None, ge=0, le=_MAX_PRICE)
    vesting_schedule: Optional[str] = None
    share_price: Optional[Decimal] = Field(None, ge=0, le=_MAX_PRICE)
    company_status: Optional[CompanyStatus] = None
    valuation_method: Optional[ValuationMethod] = None
    include_in_networth: Optional[bool] = None

    # Pension / Annuity income fields
    monthly_benefit: Optional[Decimal] = Field(None, ge=0, le=_MAX_PAYMENT)
    benefit_start_date: Optional[date] = None

    # Credit card fields
    credit_limit: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)

    # Business Equity fields
    company_valuation: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)
    ownership_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    equity_value: Optional[Decimal] = Field(None, ge=0, le=_MAX_BALANCE)

    # Tax treatment (retirement accounts)
    tax_treatment: Optional[TaxTreatment] = None

    # Employer match fields (401k / 403b)
    employer_match_percent: Optional[Decimal] = Field(None, ge=0, le=_MAX_MATCH_PCT)
    employer_match_limit_percent: Optional[Decimal] = Field(None, ge=0, le=_MAX_MATCH_PCT)
    annual_salary: Optional[Decimal] = Field(None, ge=0, le=_MAX_SALARY)

    # Property auto-valuation
    property_address: Optional[str] = None
    property_zip: Optional[str] = None

    # Vehicle auto-valuation
    vehicle_vin: Optional[str] = None
    vehicle_mileage: Optional[int] = None

    # Valuation adjustment (property + vehicle)
    valuation_adjustment_pct: Optional[Decimal] = None


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

    # Tax treatment (retirement accounts)
    tax_treatment: Optional[TaxTreatment] = None

    # Employer match fields (401k / 403b)
    employer_match_percent: Optional[Decimal] = None
    employer_match_limit_percent: Optional[Decimal] = None
    annual_salary: Optional[Decimal] = None

    # Property auto-valuation
    property_address: Optional[str] = None
    property_zip: Optional[str] = None

    # Vehicle auto-valuation
    vehicle_vin: Optional[str] = None
    vehicle_mileage: Optional[int] = None

    # Auto-valuation metadata
    last_auto_valued_at: Optional[datetime] = None

    # Valuation adjustment (property + vehicle)
    valuation_adjustment_pct: Optional[Decimal] = None

    # Interest accrual tracking
    last_interest_accrued_at: Optional[date] = None

    # Sync status (populated from linked provider items)
    last_synced_at: Optional[datetime] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    needs_reauth: Optional[bool] = None

    model_config = {"from_attributes": True}


class AccountSummary(BaseModel):
    """Account summary for lists (provider-agnostic)."""

    id: UUID
    user_id: UUID
    name: str
    account_type: AccountType
    tax_treatment: Optional[TaxTreatment] = None
    account_source: AccountSource  # plaid, teller, mx, manual
    property_type: Optional[PropertyType] = None  # For PROPERTY accounts only
    institution_name: Optional[str] = None
    mask: Optional[str] = None
    current_balance: Optional[Decimal] = None
    balance_as_of: Optional[datetime] = None
    is_active: bool
    exclude_from_cash_flow: bool
    plaid_item_hash: Optional[str] = None  # For duplicate detection

    # Equity / stock option fields
    grant_type: Optional[str] = None
    quantity: Optional[Decimal] = None
    strike_price: Optional[Decimal] = None
    share_price: Optional[Decimal] = None
    grant_date: Optional[datetime] = None
    company_status: Optional[str] = None
    vesting_schedule: Optional[str] = None

    # Provider-agnostic sync status (populated from PlaidItem, TellerEnrollment, etc.)
    provider_item_id: Optional[UUID] = None  # ID of PlaidItem or TellerEnrollment
    last_synced_at: Optional[datetime] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    needs_reauth: Optional[bool] = None

    model_config = {"from_attributes": True}
