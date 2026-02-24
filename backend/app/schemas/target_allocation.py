"""Target allocation schemas for portfolio rebalancing."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AllocationSlice(BaseModel):
    """A single slice of a target allocation."""

    asset_class: str  # 'domestic', 'international', 'bond', 'cash', 'other'
    target_percent: Decimal = Field(ge=0, le=100)
    label: str


class TargetAllocationCreate(BaseModel):
    """Schema for creating a target allocation."""

    name: str = Field(max_length=200)
    allocations: List[AllocationSlice]
    drift_threshold: Decimal = Field(default=Decimal("5.0"), ge=0, le=50)

    @model_validator(mode="after")
    def validate_allocations_sum(self) -> "TargetAllocationCreate":
        """Allocations must sum to 100 (within 0.01 tolerance)."""
        total = sum(s.target_percent for s in self.allocations)
        if abs(total - Decimal("100")) > Decimal("0.01"):
            raise ValueError(
                f"Allocation percentages must sum to 100, got {total}"
            )
        return self


class TargetAllocationUpdate(BaseModel):
    """Schema for updating a target allocation."""

    name: Optional[str] = Field(None, max_length=200)
    allocations: Optional[List[AllocationSlice]] = None
    drift_threshold: Optional[Decimal] = Field(None, ge=0, le=50)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_allocations_sum(self) -> "TargetAllocationUpdate":
        """If allocations provided, they must sum to 100 (within 0.01 tolerance)."""
        if self.allocations is not None:
            total = sum(s.target_percent for s in self.allocations)
            if abs(total - Decimal("100")) > Decimal("0.01"):
                raise ValueError(
                    f"Allocation percentages must sum to 100, got {total}"
                )
        return self


class TargetAllocationResponse(BaseModel):
    """Schema for target allocation response."""

    id: UUID
    organization_id: UUID
    user_id: Optional[UUID] = None
    name: str
    allocations: List[AllocationSlice]
    drift_threshold: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DriftItem(BaseModel):
    """A single drift analysis item for one asset class."""

    asset_class: str
    label: str
    target_percent: Decimal
    current_percent: Decimal
    current_value: Decimal
    drift_percent: Decimal  # current - target
    drift_value: Decimal
    status: str  # 'overweight', 'underweight', 'on_target'


class TradeRecommendation(BaseModel):
    """A recommended trade to rebalance one asset class."""

    asset_class: str
    label: str
    action: str  # 'BUY' or 'SELL'
    amount: Decimal
    current_value: Decimal
    target_value: Decimal
    current_percent: Decimal
    target_percent: Decimal


class RebalancingAnalysis(BaseModel):
    """Full rebalancing analysis result."""

    target_allocation_id: UUID
    target_allocation_name: str
    portfolio_total: Decimal
    drift_items: List[DriftItem]
    needs_rebalancing: bool
    max_drift_percent: Decimal
    trade_recommendations: List[TradeRecommendation]
