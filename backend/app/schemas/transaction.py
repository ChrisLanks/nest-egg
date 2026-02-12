"""Transaction schemas."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class TransactionBase(BaseModel):
    """Base transaction schema."""

    date: date
    amount: Decimal
    merchant_name: Optional[str] = None
    description: Optional[str] = None
    category_primary: Optional[str] = None
    category_detailed: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Transaction creation schema."""

    account_id: UUID
    external_transaction_id: Optional[str] = None
    is_pending: bool = False


class TransactionUpdate(BaseModel):
    """Transaction update schema."""

    merchant_name: Optional[str] = None
    description: Optional[str] = None
    category_primary: Optional[str] = None


class LabelSummary(BaseModel):
    """Label summary for transaction lists."""

    id: UUID
    name: str
    color: Optional[str] = None
    is_income: bool

    model_config = {"from_attributes": True}


class Transaction(TransactionBase):
    """Transaction response schema."""

    id: UUID
    organization_id: UUID
    account_id: UUID
    external_transaction_id: Optional[str] = None
    is_pending: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionDetail(Transaction):
    """Transaction with related data."""

    account_name: Optional[str] = None
    account_mask: Optional[str] = None
    labels: List[LabelSummary] = []

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    """Paginated transaction list response."""

    transactions: List[TransactionDetail]
    total: int
    page: int
    page_size: int
    has_more: bool


class LabelCreate(BaseModel):
    """Label creation schema."""

    name: str
    color: Optional[str] = None
    is_income: bool = False


class LabelUpdate(BaseModel):
    """Label update schema."""

    name: Optional[str] = None
    color: Optional[str] = None
    is_income: Optional[bool] = None


class LabelResponse(BaseModel):
    """Label response schema."""

    id: UUID
    organization_id: UUID
    name: str
    color: Optional[str] = None
    is_income: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
