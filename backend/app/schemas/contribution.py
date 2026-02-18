"""Contribution schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.contribution import ContributionType, ContributionFrequency


class ContributionBase(BaseModel):
    """Base contribution schema."""

    contribution_type: ContributionType
    amount: Decimal = Field(gt=0, description="Amount (dollars, shares, or percentage)")
    frequency: ContributionFrequency = ContributionFrequency.MONTHLY
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True
    notes: Optional[str] = Field(None, max_length=500)


class ContributionCreate(ContributionBase):
    """Contribution creation schema."""
class ContributionUpdate(BaseModel):
    """Contribution update schema."""

    contribution_type: Optional[ContributionType] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    frequency: Optional[ContributionFrequency] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)


class Contribution(ContributionBase):
    """Contribution response schema."""

    id: UUID
    organization_id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
