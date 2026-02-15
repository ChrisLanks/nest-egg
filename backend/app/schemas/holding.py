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
    sector: Optional[str] = None  # Financial sector (e.g., 'Technology', 'Healthcare')
    industry: Optional[str] = None  # Industry within sector (e.g., 'Software', 'Biotechnology')
    country: Optional[str] = None  # Country of domicile (e.g., 'USA', 'Germany', 'China')
    expense_ratio: Optional[Decimal] = None  # Annual expense ratio as decimal (e.g., 0.0003 = 0.03%)


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
    sector: Optional[str] = None  # Financial sector (Phase 2+)
    industry: Optional[str] = None  # Industry within sector (Phase 2+)
    country: Optional[str] = None  # Country of domicile (for international categorization)
    expense_ratio: Optional[Decimal] = None  # Annual expense ratio
    # Calculated fields
    gain_loss: Optional[Decimal] = None
    gain_loss_percent: Optional[Decimal] = None
    annual_fee: Optional[Decimal] = None  # Calculated: current_total_value * expense_ratio


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


class SectorBreakdown(BaseModel):
    """Breakdown by financial sector."""

    sector: str
    value: Decimal
    count: int
    percentage: Decimal


class TreemapNode(BaseModel):
    """Node for treemap visualization."""

    name: str
    value: Decimal
    percent: Decimal
    children: Optional[list['TreemapNode']] = None
    color: Optional[str] = None


class AccountHoldings(BaseModel):
    """Holdings for a single account."""

    account_id: UUID
    account_name: str
    account_type: str
    account_value: Decimal
    holdings: list[Holding]


class PortfolioSummary(BaseModel):
    """Portfolio summary across all investment accounts."""

    total_value: Decimal
    total_cost_basis: Optional[Decimal] = None
    total_gain_loss: Optional[Decimal] = None
    total_gain_loss_percent: Optional[Decimal] = None
    holdings_by_ticker: list[HoldingSummary]
    holdings_by_account: list[AccountHoldings]  # NEW: Holdings grouped by account

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

    # Sector breakdown (Phase 2+)
    sector_breakdown: Optional[list[SectorBreakdown]] = None

    # Fees
    total_annual_fees: Optional[Decimal] = None  # Sum of all annual fees across holdings


class StyleBoxItem(BaseModel):
    """Market cap and style breakdown item."""

    style_class: str  # e.g., "Large Cap Value", "Mid Cap Growth"
    percentage: Decimal  # % of total portfolio
    one_day_change: Optional[Decimal] = None  # 1-day % change (mocked for now)
    value: Decimal  # Total value in this category
    holding_count: int  # Number of holdings in this category


class SnapshotResponse(BaseModel):
    """Response for portfolio snapshot."""

    id: UUID
    organization_id: UUID
    snapshot_date: datetime
    total_value: Decimal
    total_cost_basis: Optional[Decimal] = None
    total_gain_loss: Optional[Decimal] = None
    total_gain_loss_percent: Optional[Decimal] = None

    model_config = {"from_attributes": True}
