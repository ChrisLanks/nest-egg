"""Recurring transaction schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.recurring_transaction import RecurringFrequency


class RecurringTransactionBase(BaseModel):
    """Base recurring transaction schema."""

    merchant_name: str
    account_id: UUID
    frequency: RecurringFrequency
    average_amount: Decimal = Field(gt=0)
    amount_variance: Decimal = Field(default=Decimal("5.00"), ge=0)
    category_id: Optional[UUID] = None
    is_bill: bool = False
    reminder_days_before: int = Field(default=3, ge=0, le=30)


class RecurringTransactionCreate(RecurringTransactionBase):
    """Schema for creating a recurring transaction."""

    pass


class RecurringTransactionUpdate(BaseModel):
    """Schema for updating a recurring transaction."""

    merchant_name: Optional[str] = None
    frequency: Optional[RecurringFrequency] = None
    average_amount: Optional[Decimal] = Field(None, gt=0)
    amount_variance: Optional[Decimal] = Field(None, ge=0)
    category_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    is_bill: Optional[bool] = None
    reminder_days_before: Optional[int] = Field(None, ge=0, le=30)


class RecurringTransactionResponse(RecurringTransactionBase):
    """Schema for recurring transaction response."""

    id: UUID
    organization_id: UUID
    description_pattern: Optional[str]
    is_user_created: bool
    confidence_score: Optional[Decimal]
    first_occurrence: date
    last_occurrence: Optional[date]
    next_expected_date: Optional[date]
    occurrence_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpcomingBillResponse(BaseModel):
    """Schema for upcoming bill reminder."""

    recurring_transaction_id: UUID
    merchant_name: str
    average_amount: Decimal
    next_expected_date: date
    days_until_due: int
    is_overdue: bool
    account_id: UUID
    category_id: Optional[UUID] = None

    class Config:
        from_attributes = True
