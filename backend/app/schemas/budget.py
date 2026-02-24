"""Budget schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.budget import BudgetPeriod


class BudgetBase(BaseModel):
    """Base budget schema."""

    name: str
    amount: Decimal = Field(gt=0)
    period: BudgetPeriod
    start_date: date
    end_date: Optional[date] = None
    category_id: Optional[UUID] = None
    label_id: Optional[UUID] = None
    rollover_unused: bool = False
    alert_threshold: Decimal = Field(default=Decimal("0.80"), ge=0, le=1)


class BudgetCreate(BudgetBase):
    """Schema for creating a budget."""

    is_shared: bool = False
    shared_user_ids: Optional[List[str]] = None


class BudgetUpdate(BaseModel):
    """Schema for updating a budget."""

    name: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    period: Optional[BudgetPeriod] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category_id: Optional[UUID] = None
    label_id: Optional[UUID] = None
    rollover_unused: Optional[bool] = None
    alert_threshold: Optional[Decimal] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None
    is_shared: Optional[bool] = None
    shared_user_ids: Optional[List[str]] = None


class BudgetResponse(BudgetBase):
    """Schema for budget response."""

    id: UUID
    organization_id: UUID
    user_id: Optional[UUID] = None
    is_active: bool
    is_shared: bool
    shared_user_ids: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BudgetSpendingResponse(BaseModel):
    """Schema for budget spending response."""

    budget_amount: Decimal
    spent: Decimal
    remaining: Decimal
    percentage: Decimal
    period_start: date
    period_end: date
