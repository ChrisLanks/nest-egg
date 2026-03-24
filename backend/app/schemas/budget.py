"""Budget schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.budget import BudgetPeriod


class BudgetBase(BaseModel):
    """Base budget schema."""

    name: str = Field(..., max_length=255)
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
    shared_user_ids: Optional[List[str]] = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_date_range(self) -> "BudgetCreate":
        """Ensure end_date >= start_date when both are provided."""
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class BudgetUpdate(BaseModel):
    """Schema for updating a budget."""

    name: Optional[str] = Field(None, max_length=255)
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
    shared_user_ids: Optional[List[str]] = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_date_range(self) -> "BudgetUpdate":
        """Ensure end_date >= start_date when both are provided."""
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date")
        return self


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
    rollover_amount: Decimal = Decimal("0.00")
    effective_budget: Optional[Decimal] = None
