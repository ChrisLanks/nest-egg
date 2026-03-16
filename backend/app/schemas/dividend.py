"""Dividend and investment income schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.dividend import IncomeType


class DividendIncomeCreate(BaseModel):
    """Create a dividend income record."""

    account_id: UUID
    holding_id: Optional[UUID] = None
    income_type: IncomeType
    ticker: str
    name: Optional[str] = None
    amount: Decimal = Field(gt=0)
    per_share_amount: Optional[Decimal] = None
    shares_held: Optional[Decimal] = None
    ex_date: Optional[date] = None
    pay_date: Optional[date] = None
    record_date: Optional[date] = None
    is_reinvested: bool = False
    reinvested_shares: Optional[Decimal] = None
    reinvested_price: Optional[Decimal] = None


class DividendIncomeUpdate(BaseModel):
    """Update a dividend income record."""

    income_type: Optional[IncomeType] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    per_share_amount: Optional[Decimal] = None
    ex_date: Optional[date] = None
    pay_date: Optional[date] = None
    is_reinvested: Optional[bool] = None
    reinvested_shares: Optional[Decimal] = None
    reinvested_price: Optional[Decimal] = None


class DividendIncomeResponse(BaseModel):
    """Dividend income response."""

    id: UUID
    organization_id: UUID
    account_id: UUID
    holding_id: Optional[UUID] = None
    income_type: IncomeType
    ticker: str
    name: Optional[str] = None
    amount: Decimal
    per_share_amount: Optional[Decimal] = None
    shares_held: Optional[Decimal] = None
    ex_date: Optional[date] = None
    pay_date: Optional[date] = None
    record_date: Optional[date] = None
    is_reinvested: bool
    reinvested_shares: Optional[Decimal] = None
    reinvested_price: Optional[Decimal] = None
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DividendByTicker(BaseModel):
    """Dividend summary for a single ticker."""

    ticker: str
    name: Optional[str] = None
    total_income: Decimal
    payment_count: int
    avg_per_share: Optional[Decimal] = None
    latest_ex_date: Optional[date] = None
    yield_on_cost: Optional[Decimal] = None  # Annual income / cost basis


class DividendByMonth(BaseModel):
    """Monthly dividend income summary."""

    month: str  # "2024-01"
    total_income: Decimal
    dividend_count: int
    by_type: Dict[str, Decimal]  # income_type → total


class DividendSummary(BaseModel):
    """Portfolio-wide dividend income summary."""

    total_income_ytd: Decimal
    total_income_trailing_12m: Decimal
    total_income_all_time: Decimal
    projected_annual_income: Decimal
    monthly_average: Decimal
    by_ticker: List[DividendByTicker]
    by_month: List[DividendByMonth]
    top_payers: List[DividendByTicker]  # Top 10 by total income
    income_growth_pct: Optional[Decimal] = None  # YoY growth


class DividendCalendarEntry(BaseModel):
    """Single entry for the dividend calendar view."""

    ticker: str
    name: Optional[str] = None
    ex_date: date
    pay_date: Optional[date] = None
    estimated_amount: Optional[Decimal] = None
    income_type: IncomeType
