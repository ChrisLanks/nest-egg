"""Account schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel

from app.models.account import AccountType, AccountSource, PropertyType


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


class AccountUpdate(BaseModel):
    """Account update schema."""

    name: Optional[str] = None
    is_active: Optional[bool] = None
    current_balance: Optional[Decimal] = None
    mask: Optional[str] = None
    exclude_from_cash_flow: Optional[bool] = None


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

    model_config = {"from_attributes": True}


class AccountSummary(BaseModel):
    """Account summary for lists."""

    id: UUID
    user_id: UUID
    name: str
    account_type: AccountType
    property_type: Optional[PropertyType] = None  # For PROPERTY accounts only
    institution_name: Optional[str] = None
    mask: Optional[str] = None
    current_balance: Optional[Decimal] = None
    balance_as_of: Optional[datetime] = None
    is_active: bool
    exclude_from_cash_flow: bool
    plaid_item_hash: Optional[str] = None  # For duplicate detection
    plaid_item_id: Optional[UUID] = None  # For sync operations

    # Sync status from PlaidItem
    last_synced_at: Optional[datetime] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    needs_reauth: Optional[bool] = None

    model_config = {"from_attributes": True}
