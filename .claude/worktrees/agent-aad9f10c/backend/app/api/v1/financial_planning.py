"""Financial planning API endpoints.

Three planning tools derived from account data + user-provided inputs:

  GET /api/v1/financial-planning/mortgage       — mortgage/refinance analyzer
  GET /api/v1/financial-planning/ss-claiming    — Social Security claiming optimizer
  GET /api/v1/financial-planning/tax-projection — estimated quarterly tax calculator

All endpoints support an optional ``user_id`` query param for household
member filtering.
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
from app.models.user import User
from app.services.mortgage_analyzer_service import MortgageAnalyzerService
from app.services.ss_claiming_strategy_service import SSClaimingStrategyService
from app.services.tax_projection_service import TaxProjectionService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Mortgage response schemas ─────────────────────────────────────────────


class AmortizationRowResponse(BaseModel):
    month: int
    payment: float
    principal: float
    interest: float
    balance: float
    cumulative_interest: float


class LoanSummaryResponse(BaseModel):
    monthly_payment: float
    total_paid: float
    total_interest: float
    total_principal: float
    payoff_months: int
    payoff_date: str


class RefinanceComparisonResponse(BaseModel):
    current: LoanSummaryResponse
    refinanced: LoanSummaryResponse
    monthly_savings: float
    lifetime_interest_savings: float
    break_even_months: int
    break_even_date: str
    recommendation: str


class ExtraPaymentImpactResponse(BaseModel):
    original_payoff_months: int
    new_payoff_months: int
    months_saved: int
    interest_saved: float
    original_total_interest: float
    new_total_interest: float


class EquityMilestoneResponse(BaseModel):
    equity_pct: int
    month: int
    date: str
    balance_at_milestone: float


class MortgageAnalysisResponse(BaseModel):
    loan_balance: float
    interest_rate: float
    monthly_payment: float
    remaining_months: int
    amortization: List[AmortizationRowResponse]
    summary: LoanSummaryResponse
    refinance: Optional[RefinanceComparisonResponse] = None
    extra_payment: Optional[ExtraPaymentImpactResponse] = None
    equity_milestones: List[EquityMilestoneResponse]
    has_mortgage: bool


# ── SS claiming response schemas ──────────────────────────────────────────


class ClaimingAgeOptionResponse(BaseModel):
    claiming_age: int
    monthly_benefit: float
    annual_benefit: float
    lifetime_pessimistic: float
    lifetime_base: float
    lifetime_optimistic: float
    breakeven_vs_62_months: Optional[int] = None


class SpousalBenefitResponse(BaseModel):
    higher_earner_pia: float
    spousal_monthly_at_fra: float
    spousal_monthly_at_62: float
    spousal_monthly_at_70: float
    note: str


class SSClaimingResponse(BaseModel):
    current_age: int
    fra_age: float
    estimated_pia: float
    options: List[ClaimingAgeOptionResponse]
    optimal_age_base_scenario: int
    optimal_age_pessimistic_scenario: int
    optimal_age_optimistic_scenario: int
    spousal: Optional[SpousalBenefitResponse] = None
    summary: str


# ── Tax projection response schemas ───────────────────────────────────────


class TaxBracketBreakdownResponse(BaseModel):
    rate: float
    income_in_bracket: float
    tax_owed: float


class QuarterlyPaymentResponse(BaseModel):
    quarter: str
    due_date: str
    amount_due: float
    paid: bool


class TaxProjectionResponse(BaseModel):
    tax_year: int
    filing_status: str
    ordinary_income: float
    self_employment_income: float
    estimated_capital_gains: float
    total_gross_income: float
    standard_deduction: float
    se_deduction: float
    additional_deductions: float
    total_deductions: float
    taxable_income: float
    ordinary_tax: float
    se_tax: float
    ltcg_tax: float
    total_tax_before_credits: float
    effective_rate: float
    marginal_rate: float
    quarterly_payments: List[QuarterlyPaymentResponse]
    total_quarterly_due: float
    prior_year_tax: Optional[float] = None
    safe_harbour_amount: Optional[float] = None
    safe_harbour_met: Optional[bool] = None
    bracket_breakdown: List[TaxBracketBreakdownResponse]
    summary: str


# ── Helpers ────────────────────────────────────────────────────────────────


async def _get_mortgage_account(
    db: AsyncSession,
    organization_id: UUID,
    user_id: Optional[UUID],
    account_id: Optional[UUID],
) -> Optional[Account]:
    """Fetch the first (or specified) mortgage account."""
    conditions = [
        Account.organization_id == organization_id,
        Account.is_active.is_(True),
        Account.account_type == AccountType.MORTGAGE,
    ]
    if user_id:
        conditions.append(Account.user_id == user_id)
    if account_id:
        conditions.append(Account.id == account_id)

    result = await db.execute(select(Account).where(and_(*conditions)).limit(1))
    return result.scalar_one_or_none()


# ── Mortgage endpoint ─────────────────────────────────────────────────────


@router.get("/mortgage", response_model=MortgageAnalysisResponse)
async def get_mortgage_analysis(
    user_id: Optional[UUID] = Query(None),
    account_id: Optional[UUID] = Query(None, description="Specific mortgage account ID"),
    refinance_rate: Optional[float] = Query(
        None, ge=0.0, le=0.30, description="New rate as decimal (e.g. 0.055)"
    ),
    refinance_term_months: Optional[int] = Query(None, ge=12, le=480),
    closing_costs: float = Query(0.0, ge=0.0, description="Up-front closing costs for refinance"),
    extra_monthly_payment: float = Query(
        0.0, ge=0.0, description="Extra principal paid each month"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MortgageAnalysisResponse:
    """
    Analyse the user's mortgage account and optionally model a refinance.

    Fetches the mortgage account balance, rate, and remaining term
    automatically. Pass ``refinance_rate`` to compare scenarios.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    account = await _get_mortgage_account(db, current_user.organization_id, user_id, account_id)

    if account is None:
        return MortgageAnalysisResponse(
            loan_balance=0,
            interest_rate=0,
            monthly_payment=0,
            remaining_months=0,
            amortization=[],
            summary=LoanSummaryResponse(
                monthly_payment=0,
                total_paid=0,
                total_interest=0,
                total_principal=0,
                payoff_months=0,
                payoff_date=date.today().isoformat(),
            ),
            equity_milestones=[],
            has_mortgage=False,
        )

    balance = float(account.current_balance or 0)
    rate = float(account.interest_rate or 0) / 100  # stored as percentage
    min_pmt = float(account.minimum_payment or 0)

    # Estimate remaining months from maturity or loan_term
    remaining: int
    if account.maturity_date:
        today = date.today()
        delta_months = (account.maturity_date.year - today.year) * 12 + (
            account.maturity_date.month - today.month
        )
        remaining = max(1, delta_months)
    elif account.loan_term_months and account.origination_date:
        months_elapsed = (date.today().year - account.origination_date.year) * 12 + (
            date.today().month - account.origination_date.month
        )
        remaining = max(1, account.loan_term_months - months_elapsed)
    else:
        # Fallback: assume 30-year loan, calculate from balance + rate
        remaining = 360

    if balance <= 0 or rate <= 0:
        return MortgageAnalysisResponse(
            loan_balance=balance,
            interest_rate=rate,
            monthly_payment=min_pmt,
            remaining_months=remaining,
            amortization=[],
            summary=LoanSummaryResponse(
                monthly_payment=min_pmt,
                total_paid=0,
                total_interest=0,
                total_principal=0,
                payoff_months=0,
                payoff_date=date.today().isoformat(),
            ),
            equity_milestones=[],
            has_mortgage=True,
        )

    result = MortgageAnalyzerService.analyze(
        current_balance=balance,
        annual_rate=rate,
        remaining_months=remaining,
        refinance_rate=refinance_rate,
        refinance_term_months=refinance_term_months,
        closing_costs=closing_costs,
        extra_monthly_payment=extra_monthly_payment,
    )

    def _row(r) -> AmortizationRowResponse:
        return AmortizationRowResponse(**vars(r))

    def _summary(s) -> LoanSummaryResponse:
        return LoanSummaryResponse(**vars(s))

    refi_resp = None
    if result.refinance:
        rf = result.refinance
        refi_resp = RefinanceComparisonResponse(
            current=_summary(rf.current),
            refinanced=_summary(rf.refinanced),
            monthly_savings=rf.monthly_savings,
            lifetime_interest_savings=rf.lifetime_interest_savings,
            break_even_months=rf.break_even_months,
            break_even_date=rf.break_even_date,
            recommendation=rf.recommendation,
        )

    extra_resp = None
    if result.extra_payment:
        extra_resp = ExtraPaymentImpactResponse(**vars(result.extra_payment))

    return MortgageAnalysisResponse(
        loan_balance=result.loan_balance,
        interest_rate=result.interest_rate,
        monthly_payment=result.monthly_payment,
        remaining_months=result.remaining_months,
        amortization=[_row(r) for r in result.amortization],
        summary=_summary(result.summary),
        refinance=refi_resp,
        extra_payment=extra_resp,
        equity_milestones=[EquityMilestoneResponse(**m) for m in result.equity_milestones],
        has_mortgage=True,
    )


# ── SS Claiming endpoint ──────────────────────────────────────────────────


@router.get("/ss-claiming", response_model=SSClaimingResponse)
async def get_ss_claiming_strategy(
    user_id: Optional[UUID] = Query(None),
    current_salary: float = Query(..., ge=0, description="Current annual gross salary"),
    birth_year: int = Query(..., ge=1940, le=2000),
    career_start_age: int = Query(22, ge=16, le=40),
    manual_pia: Optional[float] = Query(None, ge=0, description="Known PIA from SSA statement"),
    spouse_pia: Optional[float] = Query(None, ge=0, description="Spouse's estimated PIA"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSClaimingResponse:
    """
    Return Social Security claiming strategy analysis for ages 62–70.

    Compares lifetime benefits under pessimistic (die at 78), base (85),
    and optimistic (92) longevity scenarios and recommends an optimal age.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    current_age = date.today().year - birth_year

    result = SSClaimingStrategyService.analyze(
        current_salary=current_salary,
        current_age=current_age,
        birth_year=birth_year,
        career_start_age=career_start_age,
        manual_pia_override=manual_pia,
        spouse_pia=spouse_pia,
    )

    spousal_resp = None
    if result.spousal:
        spousal_resp = SpousalBenefitResponse(**vars(result.spousal))

    return SSClaimingResponse(
        current_age=result.current_age,
        fra_age=result.fra_age,
        estimated_pia=result.estimated_pia,
        options=[ClaimingAgeOptionResponse(**vars(o)) for o in result.options],
        optimal_age_base_scenario=result.optimal_age_base_scenario,
        optimal_age_pessimistic_scenario=result.optimal_age_pessimistic_scenario,
        optimal_age_optimistic_scenario=result.optimal_age_optimistic_scenario,
        spousal=spousal_resp,
        summary=result.summary,
    )


# ── Tax Projection endpoint ───────────────────────────────────────────────


@router.get("/tax-projection", response_model=TaxProjectionResponse)
async def get_tax_projection(
    user_id: Optional[UUID] = Query(None),
    filing_status: str = Query("single", pattern="^(single|married)$"),
    self_employment_income: float = Query(0.0, ge=0),
    estimated_capital_gains: float = Query(0.0, ge=0),
    additional_deductions: float = Query(
        0.0, ge=0, description="Extra itemised deductions (mortgage interest, charitable, etc.)"
    ),
    prior_year_tax: Optional[float] = Query(None, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxProjectionResponse:
    """
    Estimate current-year federal income tax and quarterly payment schedule.

    Income is automatically sourced from YTD transaction data and annualised.
    Provide ``self_employment_income`` and ``estimated_capital_gains``
    for additional income not captured in transactions.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    svc = TaxProjectionService(db)
    result = await svc.project(
        organization_id=current_user.organization_id,
        user_id=user_id,
        filing_status=filing_status,
        self_employment_income=self_employment_income,
        estimated_capital_gains=estimated_capital_gains,
        additional_deductions=additional_deductions,
        prior_year_tax=prior_year_tax,
    )

    return TaxProjectionResponse(
        tax_year=result.tax_year,
        filing_status=result.filing_status,
        ordinary_income=result.ordinary_income,
        self_employment_income=result.self_employment_income,
        estimated_capital_gains=result.estimated_capital_gains,
        total_gross_income=result.total_gross_income,
        standard_deduction=result.standard_deduction,
        se_deduction=result.se_deduction,
        additional_deductions=result.additional_deductions,
        total_deductions=result.total_deductions,
        taxable_income=result.taxable_income,
        ordinary_tax=result.ordinary_tax,
        se_tax=result.se_tax,
        ltcg_tax=result.ltcg_tax,
        total_tax_before_credits=result.total_tax_before_credits,
        effective_rate=result.effective_rate,
        marginal_rate=result.marginal_rate,
        quarterly_payments=[QuarterlyPaymentResponse(**vars(q)) for q in result.quarterly_payments],
        total_quarterly_due=result.total_quarterly_due,
        prior_year_tax=result.prior_year_tax,
        safe_harbour_amount=result.safe_harbour_amount,
        safe_harbour_met=result.safe_harbour_met,
        bracket_breakdown=[
            TaxBracketBreakdownResponse(**vars(b)) for b in result.bracket_breakdown
        ],
        summary=result.summary,
    )


# ── Savings Rate ────────────────────────────────────────────────────────────


class SavingsRateResponse(BaseModel):
    current_month_rate: Optional[float]
    trailing_3m_rate: Optional[float]
    trailing_12m_rate: Optional[float]
    monthly_trend: list
    avg_monthly_savings: float
    best_month: Optional[str]
    worst_month: Optional[str]


@router.get("/savings-rate", response_model=SavingsRateResponse)
async def get_savings_rate(
    user_id: Optional[UUID] = Query(
        None,
        description="Filter to a specific household member. Omit for combined view.",
    ),
    months: int = Query(12, ge=3, le=24),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavingsRateResponse:
    """Monthly savings rate trend for the last N calendar months."""
    if user_id:
        await verify_household_member(user_id, current_user, db)
    from app.services.savings_rate_service import SavingsRateService

    summary = await SavingsRateService.get_savings_trend(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
        months=months,
    )
    return SavingsRateResponse(**summary.model_dump())


# ── Debt Cost ───────────────────────────────────────────────────────────────


class DebtCostResponse(BaseModel):
    total_debt: float
    total_monthly_interest: float
    total_annual_interest: float
    accounts: list
    weighted_avg_rate: Optional[float]


@router.get("/debt-cost", response_model=DebtCostResponse)
async def get_debt_cost(
    user_id: Optional[UUID] = Query(
        None,
        description="Filter to a specific household member. Omit for combined view.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DebtCostResponse:
    """True monthly and annual interest cost breakdown across all debt accounts."""
    if user_id:
        await verify_household_member(user_id, current_user, db)
    from app.services.debt_cost_service import DebtCostService

    summary = await DebtCostService.get_debt_cost(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
    )
    return DebtCostResponse(**summary.model_dump())


# ── Mortgage Rate Watch ─────────────────────────────────────────────────────


class MortgageRateResponse(BaseModel):
    rate_30yr: Optional[float]
    rate_15yr: Optional[float]
    as_of_date: Optional[str]
    source: str
    your_rate: Optional[float]
    rate_comparison: Optional[str]  # "above_market" | "below_market" | "at_market" | None


@router.get("/mortgage-rates", response_model=MortgageRateResponse)
async def get_mortgage_rates(
    user_id: Optional[UUID] = Query(
        None,
        description="Filter to a specific household member for 'your rate' comparison.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MortgageRateResponse:
    """
    Current 30-yr and 15-yr fixed mortgage rates from FRED, plus a
    comparison against the user's linked mortgage account rate.
    """
    if user_id:
        await verify_household_member(user_id, current_user, db)
    from app.services.mortgage_rate_service import get_current_mortgage_rates

    rates = await get_current_mortgage_rates()

    # Fetch the user's mortgage rate for comparison
    acct = await _get_mortgage_account(db, current_user.organization_id, user_id, None)
    your_rate = float(acct.interest_rate) if acct and acct.interest_rate else None

    rate_comparison: Optional[str] = None
    if your_rate is not None and rates.rate_30yr is not None:
        diff = your_rate - rates.rate_30yr
        if diff > 0.005:  # >0.5% above market
            rate_comparison = "above_market"
        elif diff < -0.005:
            rate_comparison = "below_market"
        else:
            rate_comparison = "at_market"

    return MortgageRateResponse(
        rate_30yr=rates.rate_30yr,
        rate_15yr=rates.rate_15yr,
        as_of_date=rates.as_of_date,
        source=rates.source,
        your_rate=your_rate,
        rate_comparison=rate_comparison,
    )
