"""Savings goal schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SavingsGoalBase(BaseModel):
    """Base savings goal schema."""

    name: str
    description: Optional[str] = None
    target_amount: Decimal = Field(gt=0)
    start_date: date
    target_date: Optional[date] = None
    account_id: Optional[UUID] = None


class SavingsGoalCreate(SavingsGoalBase):
    """Schema for creating a savings goal."""

    current_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    auto_sync: bool = False


class SavingsGoalUpdate(BaseModel):
    """Schema for updating a savings goal."""

    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[Decimal] = Field(None, gt=0)
    current_amount: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    account_id: Optional[UUID] = None
    auto_sync: Optional[bool] = None


class SavingsGoalResponse(SavingsGoalBase):
    """Schema for savings goal response."""

    id: UUID
    organization_id: UUID
    current_amount: Decimal
    auto_sync: bool
    priority: Optional[int]
    is_completed: bool
    completed_at: Optional[datetime]
    is_funded: bool
    funded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SavingsGoalProgressResponse(BaseModel):
    """Schema for savings goal progress response."""

    goal_id: UUID
    name: str
    current_amount: Decimal
    target_amount: Decimal
    progress_percentage: float
    remaining_amount: Decimal
    days_elapsed: int
    days_remaining: Optional[int]
    monthly_required: Optional[Decimal]
    on_track: Optional[bool]
    is_completed: bool


class AutoSyncRequest(BaseModel):
    """Request body for auto-syncing all goals from linked accounts."""

    method: Literal["waterfall", "proportional"] = "waterfall"


class ReorderRequest(BaseModel):
    """Request body for reordering goals."""

    goal_ids: List[UUID]
