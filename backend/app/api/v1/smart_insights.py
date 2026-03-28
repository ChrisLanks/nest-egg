"""Smart financial insights API endpoints.

Provides three groups of proactive planning insights derived entirely from
the user's own account data — no manual input required:

  GET /api/v1/smart-insights/           — general planning insights
  GET /api/v1/smart-insights/roth-conversion  — Roth conversion optimizer
  GET /api/v1/smart-insights/fund-fees  — fund expense-ratio analysis

Visibility contract
-------------------
The frontend uses the ``has_*`` flags in the insights response to decide
whether to show or hide navigation items.  All three endpoints return these
flags so a single fetch is sufficient for routing decisions.

  has_retirement_accounts – user has at least one IRA / 401k / 403b / etc.
  has_taxable_investments  – user has at least one brokerage account
  has_investment_holdings  – user has holdings with price data
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, verify_household_member
from app.models.account import Account, AccountType
from app.models.holding import Holding
from app.models.user import User
from app.services.fund_fee_analyzer_service import FundFeeAnalyzerService
from app.services.roth_conversion_service import (
    RothConversionInput,
    RothConversionService,
)
from app.services.smart_insights_service import (
    TAXABLE_INVESTMENT_TYPES,
    TRADITIONAL_RETIREMENT_TYPES,
    SmartInsightsService,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Account type sets used for has_* flags ─────────────────────────────────
_ALL_RETIREMENT_TYPES = frozenset(
    {
        AccountType.RETIREMENT_401K,
        AccountType.RETIREMENT_403B,
        AccountType.RETIREMENT_457B,
        AccountType.RETIREMENT_IRA,
        AccountType.RETIREMENT_ROTH,
        AccountType.RETIREMENT_SEP_IRA,
        AccountType.RETIREMENT_SIMPLE_IRA,
    }
)


# ── Response schemas ───────────────────────────────────────────────────────


class InsightItem(BaseModel):
    type: str
    title: str
    message: str
    action: str
    priority: str
    category: str
    icon: str
    priority_score: float
    amount: Optional[float] = None
    # Human-readable label describing what `amount` represents, e.g.
    # "Annual fee drag", "Opportunity", "Shortfall", "Savings".
    # Shown in the UI next to the dollar figure so users know what it means.
    amount_label: Optional[str] = None
    # data_vintage / data_is_stale are only set for insights that use
    # periodically-updated reference data (e.g. net_worth_benchmark).
    # null on all other insight types.
    data_vintage: Optional[str] = None
    data_is_stale: Optional[bool] = None


class SmartInsightsResponse(BaseModel):
    insights: List[InsightItem]
    has_retirement_accounts: bool
    has_taxable_investments: bool
    has_investment_holdings: bool


class RothConversionYearResponse(BaseModel):
    year: int
    age: int
    optimal_conversion: float
    marginal_rate_at_conversion: float
    rmd_amount: float
    traditional_balance_start: float
    roth_balance_start: float
    traditional_balance_end: float
    roth_balance_end: float
    tax_cost_of_conversion: float
    notes: List[str]


class RothConversionResponse(BaseModel):
    years: List[RothConversionYearResponse]
    total_converted: float
    total_tax_cost: float
    no_conversion_traditional_end: float
    no_conversion_roth_end: float
    with_conversion_traditional_end: float
    with_conversion_roth_end: float
    estimated_tax_savings: float
    summary: str
    has_retirement_accounts: bool
    data_source: Optional[dict] = None  # DataSourceMeta — static/cached/live indicator


class HoldingFeeDetailResponse(BaseModel):
    ticker: Optional[str] = None
    name: Optional[str] = None
    market_value: float
    expense_ratio: float
    annual_fee: float
    ten_year_drag: float
    twenty_year_drag: float
    flag: str
    suggestion: Optional[str] = None
    is_estimated: bool = False


class FundFeeResponse(BaseModel):
    total_invested: float
    holdings_with_er_data: int
    holdings_missing_er_data: int
    annual_fee_drag: float
    weighted_avg_expense_ratio: float
    benchmark_expense_ratio: float
    ten_year_impact_vs_benchmark: float
    twenty_year_impact_vs_benchmark: float
    high_cost_count: int
    holdings: List[HoldingFeeDetailResponse]
    summary: str
    has_investment_holdings: bool


# ── Helpers ────────────────────────────────────────────────────────────────


async def _account_flags(
    db: AsyncSession,
    organization_id: UUID,
    user_id: Optional[UUID],
) -> tuple[bool, bool, bool]:
    """Return (has_retirement, has_taxable, has_holdings)."""
    conditions = [
        Account.organization_id == organization_id,
        Account.is_active.is_(True),
    ]
    if user_id:
        conditions.append(Account.user_id == user_id)

    result = await db.execute(select(Account.account_type).where(and_(*conditions)))
    types = {r for (r,) in result.all()}

    has_retirement = bool(types & _ALL_RETIREMENT_TYPES)
    has_taxable = bool(types & TAXABLE_INVESTMENT_TYPES)

    # Check for any holdings with price data
    holding_conditions = [
        Account.organization_id == organization_id,
        Account.is_active.is_(True),
        Holding.current_total_value > 0,
    ]
    if user_id:
        holding_conditions.append(Account.user_id == user_id)

    h_result = await db.execute(
        select(Holding.id)
        .join(Account, Holding.account_id == Account.id)
        .where(and_(*holding_conditions))
        .limit(1)
    )
    has_holdings = h_result.first() is not None

    return has_retirement, has_taxable, has_holdings


async def _get_account_balances(
    db: AsyncSession,
    organization_id: UUID,
    user_id: Optional[UUID],
) -> dict:
    """Sum balances by account type for Roth conversion inputs."""
    conditions = [
        Account.organization_id == organization_id,
        Account.is_active.is_(True),
    ]
    if user_id:
        conditions.append(Account.user_id == user_id)

    result = await db.execute(
        select(Account.account_type, Account.current_balance).where(and_(*conditions))
    )
    rows = result.all()

    traditional = sum(
        float(bal or 0) for atype, bal in rows if atype in TRADITIONAL_RETIREMENT_TYPES
    )
    roth = sum(float(bal or 0) for atype, bal in rows if atype == AccountType.RETIREMENT_ROTH)
    return {"traditional": traditional, "roth": roth}


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("", response_model=SmartInsightsResponse)
async def get_smart_insights(
    user_id: Optional[UUID] = Query(
        None, description="Filter to a specific household member. None = household view."
    ),
    max_insights: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SmartInsightsResponse:
    """
    Return proactive financial planning insights derived from live account data.

    Each insight is only included when the relevant account types or holdings
    are present — missing data means the check is silently skipped.

    The ``has_*`` flags drive frontend navigation visibility decisions.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    birthdate: Optional[date] = getattr(current_user, "birthdate", None)

    service = SmartInsightsService(db)
    raw_insights = await service.get_insights(
        organization_id=current_user.organization_id,
        user_id=user_id,
        user_birthdate=birthdate,
        max_insights=max_insights,
    )

    has_retirement, has_taxable, has_holdings = await _account_flags(
        db, current_user.organization_id, user_id
    )

    return SmartInsightsResponse(
        insights=[InsightItem(**i) for i in raw_insights],
        has_retirement_accounts=has_retirement,
        has_taxable_investments=has_taxable,
        has_investment_holdings=has_holdings,
    )


@router.get("/roth-conversion", response_model=RothConversionResponse)
async def get_roth_conversion(
    user_id: Optional[UUID] = Query(None),
    current_income: float = Query(
        ...,
        ge=0,
        description="Gross annual income excluding any Roth conversion amount.",
    ),
    filing_status: str = Query(
        "single",
        description="'single' or 'married'.",
        pattern="^(single|married)$",
    ),
    expected_return: float = Query(0.07, ge=0.0, le=0.20),
    years_to_project: int = Query(20, ge=1, le=40),
    respect_irmaa: bool = Query(True, description="Cap conversions to avoid IRMAA tier crossings."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RothConversionResponse:
    """
    Calculate the optimal annual Roth conversion amount.

    Balances are fetched automatically from the user's connected accounts.
    The optimizer finds the conversion amount that fills the current tax
    bracket without crossing into the next bracket or an IRMAA tier.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    has_retirement, _, _ = await _account_flags(db, current_user.organization_id, user_id)

    balances = await _get_account_balances(db, current_user.organization_id, user_id)

    birthdate: Optional[date] = getattr(current_user, "birthdate", None)
    current_age = 45  # sensible default
    if birthdate:
        current_age = (date.today() - birthdate).days // 365

    inp = RothConversionInput(
        traditional_balance=balances["traditional"],
        roth_balance=balances["roth"],
        current_income=current_income,
        current_age=current_age,
        filing_status=filing_status,
        expected_return=expected_return,
        years_to_project=years_to_project,
        respect_irmaa=respect_irmaa,
    )

    svc = RothConversionService()
    result = svc.optimize(inp)

    return RothConversionResponse(
        years=[RothConversionYearResponse(**vars(y)) for y in result.years],
        total_converted=result.total_converted,
        total_tax_cost=result.total_tax_cost,
        no_conversion_traditional_end=result.no_conversion_traditional_end,
        no_conversion_roth_end=result.no_conversion_roth_end,
        with_conversion_traditional_end=result.with_conversion_traditional_end,
        with_conversion_roth_end=result.with_conversion_roth_end,
        estimated_tax_savings=result.estimated_tax_savings,
        summary=result.summary,
        has_retirement_accounts=has_retirement,
    )


@router.get("/fund-fees", response_model=FundFeeResponse)
async def get_fund_fees(
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FundFeeResponse:
    """
    Analyse fund expense ratios across all investment holdings.

    Returns per-holding fee details sorted by annual fee drag (highest first),
    plus a portfolio-level weighted-average ER and 10/20-year compounding impact.
    Holdings without expense ratio data are included with ``flag='no_data'``.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    has_retirement, has_taxable, has_holdings = await _account_flags(
        db, current_user.organization_id, user_id
    )

    # Fetch all holdings
    conditions = [
        Account.organization_id == current_user.organization_id,
        Account.is_active.is_(True),
        Holding.current_total_value > 0,
    ]
    if user_id:
        conditions.append(Account.user_id == user_id)

    result = await db.execute(
        select(
            Holding.ticker,
            Holding.name,
            Holding.current_total_value,
            Holding.expense_ratio,
            Holding.asset_class,
            Holding.asset_type,
        )
        .join(Account, Holding.account_id == Account.id)
        .where(and_(*conditions))
    )
    holding_rows = [
        {
            "ticker": r.ticker,
            "name": r.name,
            "current_total_value": float(r.current_total_value),
            "expense_ratio": float(r.expense_ratio) if r.expense_ratio is not None else None,
            "asset_class": r.asset_class,
            "asset_type": r.asset_type,
        }
        for r in result.all()
    ]

    analysis = FundFeeAnalyzerService.analyze(holding_rows)

    return FundFeeResponse(
        **analysis.to_dict(),
        has_investment_holdings=has_holdings,
    )
