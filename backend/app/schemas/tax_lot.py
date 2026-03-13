"""Tax lot schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class TaxLotBase(BaseModel):
    """Base tax lot schema."""

    acquisition_date: date
    quantity: Decimal
    cost_basis_per_share: Decimal


class TaxLotCreate(TaxLotBase):
    """Schema for manually recording a purchase lot."""

    pass


class TaxLotResponse(TaxLotBase):
    """Tax lot response schema."""

    id: UUID
    organization_id: UUID
    holding_id: UUID
    account_id: UUID
    total_cost_basis: Decimal
    remaining_quantity: Decimal
    is_closed: bool
    closed_at: Optional[datetime] = None
    sale_proceeds: Optional[Decimal] = None
    realized_gain_loss: Optional[Decimal] = None
    holding_period: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SaleRequest(BaseModel):
    """Schema for recording a sale against tax lots."""

    quantity: Decimal
    sale_price_per_share: Decimal
    sale_date: date
    cost_basis_method: Optional[str] = None  # Override account default
    specific_lot_ids: Optional[List[UUID]] = None  # For specific_id method


class SaleResult(BaseModel):
    """Result of a sale operation."""

    total_proceeds: Decimal
    total_cost_basis: Decimal
    realized_gain_loss: Decimal
    short_term_gain_loss: Decimal
    long_term_gain_loss: Decimal
    lots_affected: int
    lot_details: List[TaxLotResponse]


class UnrealizedGainItem(BaseModel):
    """Per-lot unrealized gain/loss."""

    lot_id: UUID
    holding_id: UUID
    ticker: str
    acquisition_date: date
    quantity: Decimal
    cost_basis_per_share: Decimal
    current_price_per_share: Optional[Decimal] = None
    unrealized_gain_loss: Optional[Decimal] = None
    holding_period: str  # SHORT_TERM or LONG_TERM


class UnrealizedGainsSummary(BaseModel):
    """Per-account unrealized gains summary."""

    account_id: UUID
    total_unrealized_gain_loss: Decimal
    short_term_unrealized: Decimal
    long_term_unrealized: Decimal
    lots: List[UnrealizedGainItem]


class RealizedGainsSummary(BaseModel):
    """Tax year realized gains summary."""

    tax_year: int
    total_realized_gain_loss: Decimal
    short_term_gain_loss: Decimal
    long_term_gain_loss: Decimal
    total_proceeds: Decimal
    total_cost_basis: Decimal
    lots_closed: int


class CostBasisMethodUpdate(BaseModel):
    """Schema for updating account cost basis method."""

    cost_basis_method: str  # fifo, lifo, hifo, specific_id
