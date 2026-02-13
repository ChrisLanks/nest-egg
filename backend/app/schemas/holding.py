"""Holding schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class HoldingBase(BaseModel):
    """Base holding schema."""

    ticker: str
    name: Optional[str] = None
    shares: Decimal
    cost_basis_per_share: Optional[Decimal] = None
    asset_type: Optional[str] = None  # 'stock', 'bond', 'etf', 'mutual_fund', 'cash', 'other'


class HoldingCreate(HoldingBase):
    """Holding creation schema."""

    account_id: UUID


class HoldingUpdate(BaseModel):
    """Holding update schema."""

    ticker: Optional[str] = None
    name: Optional[str] = None
    shares: Optional[Decimal] = None
    cost_basis_per_share: Optional[Decimal] = None
    current_price_per_share: Optional[Decimal] = None
    asset_type: Optional[str] = None


class Holding(HoldingBase):
    """Holding response schema."""

    id: UUID
    account_id: UUID
    organization_id: UUID
    total_cost_basis: Optional[Decimal] = None
    current_price_per_share: Optional[Decimal] = None
    current_total_value: Optional[Decimal] = None
    price_as_of: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HoldingSummary(BaseModel):
    """Holdings summary for portfolio view."""

    ticker: str
    name: Optional[str] = None
    total_shares: Decimal
    total_cost_basis: Optional[Decimal] = None
    current_price_per_share: Optional[Decimal] = None
    current_total_value: Optional[Decimal] = None
    price_as_of: Optional[datetime] = None
    asset_type: Optional[str] = None
    # Calculated fields
    gain_loss: Optional[Decimal] = None
    gain_loss_percent: Optional[Decimal] = None


class CategoryBreakdown(BaseModel):
    """Breakdown by category (retirement, taxable, etc.)."""

    retirement_value: Decimal = Decimal('0')
    retirement_percent: Optional[Decimal] = None
    taxable_value: Decimal = Decimal('0')
    taxable_percent: Optional[Decimal] = None
    other_value: Decimal = Decimal('0')
    other_percent: Optional[Decimal] = None


class GeographicBreakdown(BaseModel):
    """Geographic allocation breakdown."""

    domestic_value: Decimal = Decimal('0')
    domestic_percent: Optional[Decimal] = None
    international_value: Decimal = Decimal('0')
    international_percent: Optional[Decimal] = None
    unknown_value: Decimal = Decimal('0')
    unknown_percent: Optional[Decimal] = None


class TreemapNode(BaseModel):
    """Node for treemap visualization."""

    name: str
    value: Decimal
    percent: Decimal
    children: Optional[list['TreemapNode']] = None
    color: Optional[str] = None


class PortfolioSummary(BaseModel):
    """Portfolio summary across all investment accounts."""

    total_value: Decimal
    total_cost_basis: Optional[Decimal] = None
    total_gain_loss: Optional[Decimal] = None
    total_gain_loss_percent: Optional[Decimal] = None
    holdings_by_ticker: list[HoldingSummary]

    # Asset allocation
    stocks_value: Decimal = Decimal('0')
    bonds_value: Decimal = Decimal('0')
    etf_value: Decimal = Decimal('0')
    mutual_funds_value: Decimal = Decimal('0')
    cash_value: Decimal = Decimal('0')
    other_value: Decimal = Decimal('0')

    # Enhanced breakdowns
    category_breakdown: Optional[CategoryBreakdown] = None
    geographic_breakdown: Optional[GeographicBreakdown] = None

    # Treemap data
    treemap_data: Optional[TreemapNode] = None
