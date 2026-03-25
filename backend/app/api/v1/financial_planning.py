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
from app.services.dashboard_service import DashboardService
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


class FileAndSuspendResponse(BaseModel):
    worker_birth_year: int
    worker_fra: float
    can_suspend: bool
    monthly_gain_per_year_suspended: float
    max_gain_age: int
    suspension_note: str
    restricted_app_eligible: bool
    restricted_app_note: str
    joint_strategy_summary: str


class SSClaimingResponse(BaseModel):
    current_age: int
    fra_age: float
    estimated_pia: float
    options: List[ClaimingAgeOptionResponse]
    optimal_age_base_scenario: int
    optimal_age_pessimistic_scenario: int
    optimal_age_optimistic_scenario: int
    spousal: Optional[SpousalBenefitResponse] = None
    file_and_suspend: Optional[FileAndSuspendResponse] = None
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
    state: Optional[str] = None
    state_tax: float = 0.0
    state_tax_rate: float = 0.0
    combined_tax: float = 0.0
    combined_effective_rate: float = 0.0
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
    current_user_id: Optional[UUID] = None,
) -> Optional[Account]:
    """Fetch the first (or specified) mortgage account.

    When account_id is provided without an explicit user_id, ownership is
    scoped to current_user_id to prevent cross-member account exposure.
    """
    conditions = [
        Account.organization_id == organization_id,
        Account.is_active.is_(True),
        Account.account_type == AccountType.MORTGAGE,
    ]
    # Resolve effective owner: explicit user_id takes priority, then fall back
    # to the requesting user when looking up a specific account.
    effective_user_id = user_id or (current_user_id if account_id else None)
    if effective_user_id:
        conditions.append(Account.user_id == effective_user_id)
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

    account = await _get_mortgage_account(db, current_user.organization_id, user_id, account_id, current_user_id=current_user.id)

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

    balance = abs(float(account.current_balance or 0))  # stored as negative (liability)
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

    fas_resp = None
    if result.file_and_suspend:
        fas_resp = FileAndSuspendResponse(**vars(result.file_and_suspend))

    return SSClaimingResponse(
        current_age=result.current_age,
        fra_age=result.fra_age,
        estimated_pia=result.estimated_pia,
        options=[ClaimingAgeOptionResponse(**vars(o)) for o in result.options],
        optimal_age_base_scenario=result.optimal_age_base_scenario,
        optimal_age_pessimistic_scenario=result.optimal_age_pessimistic_scenario,
        optimal_age_optimistic_scenario=result.optimal_age_optimistic_scenario,
        spousal=spousal_resp,
        file_and_suspend=fas_resp,
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
    state: Optional[str] = Query(None, max_length=2, description="Two-letter state abbreviation for state income tax estimate (e.g. 'CA', 'TX')"),
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
        state=state,
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
        state=result.state,
        state_tax=result.state_tax,
        state_tax_rate=result.state_tax_rate,
        combined_tax=result.combined_tax,
        combined_effective_rate=result.combined_effective_rate,
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
        await verify_household_member(db, user_id, current_user.organization_id)
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
        await verify_household_member(db, user_id, current_user.organization_id)
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
        await verify_household_member(db, user_id, current_user.organization_id)
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


# ── Guardrails / Sequence-of-Returns Stress Test ──────────────────────────


class YearStatsResponse(BaseModel):
    year: int
    age: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    mean: float
    pct_depleted: float


class GuardrailsResponse(BaseModel):
    initial_portfolio: float
    initial_annual_spending: float
    initial_withdrawal_rate: float
    crash_scenario_name: str
    crash_first_year_return: float
    guardrails_enabled: bool
    success_rate: float
    median_final_portfolio: float
    p10_final_portfolio: float
    p90_final_portfolio: float
    yearly_stats: List[YearStatsResponse]
    median_spending_path: List[float]
    num_simulations: int
    years_simulated: int
    data_note: str


@router.get("/guardrails-stress-test", response_model=GuardrailsResponse)
async def get_guardrails_stress_test(
    initial_portfolio: float = Query(..., gt=0, description="Portfolio value at retirement"),
    annual_spending: float = Query(..., gt=0, description="Annual spending in today's dollars"),
    current_age: int = Query(..., ge=40, le=90),
    life_expectancy: int = Query(90, ge=60, le=110),
    crash_scenario: str = Query(
        "2008_financial_crisis",
        description="Crash scenario: 2008_financial_crisis | 2000_dot_com | 1973_oil_shock",
    ),
    crash_return_override: Optional[float] = Query(
        None, ge=-1.0, le=0.0, description="Custom first-year return (e.g. -0.40 for -40%)"
    ),
    guardrails_enabled: bool = Query(True, description="Apply Guyton-Klinger spending rules"),
    num_simulations: int = Query(1_000, ge=100, le=5_000),
    current_user: User = Depends(get_current_user),
) -> GuardrailsResponse:
    """
    Sequence-of-returns stress test with optional Guyton-Klinger guardrails.

    Simulates retiring into an immediate severe market crash (year 1) and
    models portfolio survival across Monte Carlo paths.  Guardrails
    dynamically raise or cut spending to protect the portfolio.

    **Data note**: crash scenario returns are from historical market data
    (NYU Stern Damodaran dataset, as of 2024).  Long-run return assumptions
    are from financial.py FIRE constants.
    """
    from app.services.retirement.guardrails_service import run_guardrails_simulation

    result = run_guardrails_simulation(
        initial_portfolio=initial_portfolio,
        annual_spending=annual_spending,
        current_age=current_age,
        life_expectancy=life_expectancy,
        crash_scenario=crash_scenario,
        crash_return_override=crash_return_override,
        guardrails_enabled=guardrails_enabled,
        num_simulations=num_simulations,
    )

    return GuardrailsResponse(
        initial_portfolio=result.initial_portfolio,
        initial_annual_spending=result.initial_annual_spending,
        initial_withdrawal_rate=result.initial_withdrawal_rate,
        crash_scenario_name=result.crash_scenario_name,
        crash_first_year_return=result.crash_first_year_return,
        guardrails_enabled=result.guardrails_enabled,
        success_rate=result.success_rate,
        median_final_portfolio=result.median_final_portfolio,
        p10_final_portfolio=result.p10_final_portfolio,
        p90_final_portfolio=result.p90_final_portfolio,
        yearly_stats=[YearStatsResponse(**vars(s)) for s in result.yearly_stats],
        median_spending_path=result.median_spending_path,
        num_simulations=result.num_simulations,
        years_simulated=result.years_simulated,
        data_note=result.data_note,
    )


# ── Dependent Care FSA Optimizer ──────────────────────────────────────────


class DependentCareResponse(BaseModel):
    tax_year: int
    annual_childcare_expenses: float
    num_dependents: int
    agi: float
    marginal_rate: float
    filing_status: str
    dcfsa_contribution: float
    dcfsa_tax_savings: float
    dcfsa_limit: float
    cdctc_eligible_expenses: float
    cdctc_rate: float
    cdctc_credit: float
    total_benefit: float
    effective_childcare_cost: float
    effective_cost_pct: float
    credit_only_benefit: float
    fsa_only_benefit: float
    combined_benefit: float
    recommendation: str
    data_note: str


@router.get("/dependent-care-optimizer", response_model=DependentCareResponse)
async def get_dependent_care_optimization(
    annual_childcare_expenses: float = Query(..., ge=0, description="Total annual qualified childcare costs"),
    num_dependents: int = Query(1, ge=1, le=10),
    agi: float = Query(..., ge=0, description="Adjusted gross income"),
    marginal_rate: float = Query(..., ge=0.0, le=0.50, description="Federal marginal tax rate as decimal"),
    filing_status: str = Query("mfj", pattern="^(mfj|mfs|single|hoh)$"),
    current_user: User = Depends(get_current_user),
) -> DependentCareResponse:
    """
    Optimise the split between DC-FSA and Child/Dependent Care Tax Credit (CDCTC).

    Returns tax savings under three strategies (FSA only, credit only, combined)
    and recommends the most beneficial approach for your tax situation.

    **Data note**: Limits from IRS Publication 503 / IRC §129 (static; rarely
    changes year-to-year). UI displays the tax year and a link to irs.gov/p503.
    """
    from app.services.dependent_care_optimizer_service import optimize_dependent_care

    result = optimize_dependent_care(
        annual_childcare_expenses=annual_childcare_expenses,
        num_dependents=num_dependents,
        agi=agi,
        marginal_rate=marginal_rate,
        filing_status=filing_status,
    )
    return DependentCareResponse(**vars(result))


# ── Survivor Income Scenario ──────────────────────────────────────────────


class SurvivorYearResponse(BaseModel):
    year: int
    survivor_age: int
    portfolio_value: float
    annual_income: float
    annual_spending: float
    net_cash_flow: float


class SurvivorScenarioResponse(BaseModel):
    death_age_of_deceased: int
    survivor_current_age: int
    survivor_life_expectancy: int
    joint_portfolio_at_death: float
    joint_annual_income_at_death: float
    joint_annual_spending: float
    survivor_ss_benefit: float
    survivor_ss_is_own: bool
    survivor_annual_income: float
    survivor_annual_spending: float
    survivor_income_gap: float
    projection: List[SurvivorYearResponse]
    success_rate: float
    median_final_portfolio: float
    data_note: str


@router.get("/survivor-scenario", response_model=SurvivorScenarioResponse)
async def get_survivor_scenario(
    death_age: int = Query(..., ge=50, le=100, description="Age of deceased spouse at death"),
    deceased_ss_monthly: float = Query(0.0, ge=0, description="Deceased's monthly SS benefit"),
    deceased_pia: float = Query(0.0, ge=0, description="Deceased's PIA (for SSA 82.5% floor)"),
    survivor_current_age: int = Query(..., ge=40, le=100),
    survivor_life_expectancy: int = Query(90, ge=60, le=110),
    survivor_own_ss_monthly: float = Query(0.0, ge=0),
    survivor_ss_claiming_age: int = Query(67, ge=60, le=70),
    current_portfolio: float = Query(..., ge=0),
    joint_annual_income: float = Query(..., ge=0),
    joint_annual_spending: float = Query(..., ge=0),
    spending_reduction_pct: float = Query(0.20, ge=0.0, le=0.50),
    current_user: User = Depends(get_current_user),
) -> SurvivorScenarioResponse:
    """
    Model the surviving spouse's finances if the other partner dies at a specified age.

    Applies SSA survivor benefit rules (POMS RS 00207.010) to determine the
    survivor's Social Security benefit and projects the portfolio through their
    life expectancy.

    **Data note**: Survivor benefit reduction factors are statutory (BBA 2015 /
    SSA POMS RS 00207.010) and do not change annually.
    """
    from app.services.survivor_scenario_service import compute_survivor_scenario

    result = compute_survivor_scenario(
        death_age=death_age,
        deceased_ss_monthly=deceased_ss_monthly,
        deceased_pia=deceased_pia,
        survivor_current_age=survivor_current_age,
        survivor_life_expectancy=survivor_life_expectancy,
        survivor_own_ss_monthly=survivor_own_ss_monthly,
        survivor_ss_claiming_age=survivor_ss_claiming_age,
        current_portfolio=current_portfolio,
        joint_annual_income=joint_annual_income,
        joint_annual_spending=joint_annual_spending,
        spending_reduction_pct=spending_reduction_pct,
    )

    return SurvivorScenarioResponse(
        death_age_of_deceased=result.death_age_of_deceased,
        survivor_current_age=result.survivor_current_age,
        survivor_life_expectancy=result.survivor_life_expectancy,
        joint_portfolio_at_death=result.joint_portfolio_at_death,
        joint_annual_income_at_death=result.joint_annual_income_at_death,
        joint_annual_spending=result.joint_annual_spending,
        survivor_ss_benefit=result.survivor_ss_benefit,
        survivor_ss_is_own=result.survivor_ss_is_own,
        survivor_annual_income=result.survivor_annual_income,
        survivor_annual_spending=result.survivor_annual_spending,
        survivor_income_gap=result.survivor_income_gap,
        projection=[SurvivorYearResponse(**vars(y)) for y in result.projection],
        success_rate=result.success_rate,
        median_final_portfolio=result.median_final_portfolio,
        data_note=result.data_note,
    )


# ── Inheritance / Multi-generational Wealth Projection ────────────────────


class SpendDownScenarioResponse(BaseModel):
    strategy_name: str
    annual_withdrawal: float
    withdrawal_rate: float
    final_portfolio: float
    final_portfolio_real: float
    estate_before_tax: float
    federal_estate_tax: float
    net_to_heirs: float
    years_projected: int
    depleted_at_year: Optional[int] = None
    annual_values: List[float]


class InheritanceProjectionResponse(BaseModel):
    initial_portfolio: float
    annual_income: float
    current_age: int
    life_expectancy: int
    scenarios: List[SpendDownScenarioResponse]
    estate_tax_exemption: float
    estate_tax_rate: float
    tcja_sunset_applies: bool
    data_note: str


@router.get("/inheritance-projection", response_model=InheritanceProjectionResponse)
async def get_inheritance_projection(
    initial_portfolio: float = Query(..., gt=0),
    annual_income: float = Query(0.0, ge=0, description="Annual SS + pension income"),
    annual_spending: float = Query(..., gt=0, description="Annual household spending"),
    current_age: int = Query(..., ge=40, le=100),
    life_expectancy: int = Query(90, ge=60, le=110),
    other_assets: float = Query(0.0, ge=0, description="Non-portfolio assets (home, etc.)"),
    legacy_target: Optional[float] = Query(None, ge=0, description="Desired estate in today's dollars"),
    current_user: User = Depends(get_current_user),
) -> InheritanceProjectionResponse:
    """
    Project what heirs receive under four spend-down strategies.

    Strategies: 4% rule, minimum distributions only, spend-to-zero,
    and a user-specified legacy target.  Applies federal estate tax where
    applicable (state taxes not modelled).

    **Data note**: Estate tax exemption from IRS Rev. Proc. (updated annually).
    TCJA enhanced exemption sunsets after 2025 — UI surfaces a warning.
    """
    from app.services.inheritance_projection_service import project_inheritance

    result = project_inheritance(
        initial_portfolio=initial_portfolio,
        annual_income=annual_income,
        annual_spending=annual_spending,
        current_age=current_age,
        life_expectancy=life_expectancy,
        other_assets=other_assets,
        legacy_target=legacy_target,
    )

    return InheritanceProjectionResponse(
        initial_portfolio=result.initial_portfolio,
        annual_income=result.annual_income,
        current_age=result.current_age,
        life_expectancy=result.life_expectancy,
        scenarios=[SpendDownScenarioResponse(**vars(s)) for s in result.scenarios],
        estate_tax_exemption=result.estate_tax_exemption,
        estate_tax_rate=result.estate_tax_rate,
        tcja_sunset_applies=result.tcja_sunset_applies,
        data_note=result.data_note,
    )


# ── Household Net Worth Breakdown ─────────────────────────────────────────


class MemberNetWorthResponse(BaseModel):
    user_id: Optional[UUID] = None
    display_name: str
    total_assets: float
    total_debts: float
    net_worth: float
    account_count: int
    accounts_by_type: dict


class HouseholdNetWorthResponse(BaseModel):
    organization_id: UUID
    total_net_worth: float
    total_assets: float
    total_debts: float
    members: List[MemberNetWorthResponse]
    member_count: int


@router.get("/household-net-worth-breakdown", response_model=HouseholdNetWorthResponse)
async def get_household_net_worth_breakdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HouseholdNetWorthResponse:
    """
    Break down household net worth by individual member.

    Returns one entry per household member (attributed by account ownership)
    plus a "Joint / Unattributed" bucket for accounts with no owner.
    Useful for couples wanting to see "his / hers / joint" net worth.
    """
    from app.services.household_net_worth_service import get_household_net_worth_breakdown

    result = await get_household_net_worth_breakdown(
        db=db,
        organization_id=current_user.organization_id,
    )

    return HouseholdNetWorthResponse(
        organization_id=result.organization_id,
        total_net_worth=result.total_net_worth,
        total_assets=result.total_assets,
        total_debts=result.total_debts,
        members=[
            MemberNetWorthResponse(
                user_id=m.user_id,
                display_name=m.display_name,
                total_assets=m.total_assets,
                total_debts=m.total_debts,
                net_worth=m.net_worth,
                account_count=m.account_count,
                accounts_by_type=m.accounts_by_type,
            )
            for m in result.members
        ],
        member_count=result.member_count,
    )


# ── Inflation-Linked Asset Tracking ──────────────────────────────────────


class InflationLinkedHoldingResponse(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    current_balance: float
    ibond_fixed_rate: Optional[float] = None
    ibond_composite_rate: Optional[float] = None
    nominal_return: Optional[float] = None
    real_return: Optional[float] = None
    cpi_is_estimated: bool
    ibond_rate_is_stale: bool
    data_note: str


class InflationTrackingResponse(BaseModel):
    total_inflation_linked: float
    total_portfolio: float
    inflation_linked_pct: float
    holdings: List[InflationLinkedHoldingResponse]
    cpi_rate: float
    cpi_is_estimated: bool
    ibond_fixed_rate: float
    ibond_composite_rate: float
    ibond_rate_is_stale: bool
    ibond_rate_as_of: str
    generic_real_return: float
    data_note: str


@router.get("/inflation-tracking", response_model=InflationTrackingResponse)
async def get_inflation_tracking(
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InflationTrackingResponse:
    """
    Analyse inflation-linked assets (I-Bonds, TIPS) in the portfolio.

    Shows current CPI rate (fetched from BLS API, fallback to static table),
    I-Bond composite rate, and real vs nominal return for each holding.

    **Data note**: CPI sourced from BLS public API (no key required). Falls
    back to static table if unavailable — UI shows "CPI estimated" notice.
    I-Bond fixed rate from TreasuryDirect history table in financial constants.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    from sqlalchemy import and_, select

    from app.models.account import Account, AccountType as AT
    from app.services.inflation_tracking_service import analyze_inflation_linked_accounts

    inflation_types = {AT.TIPS, AT.I_BOND}
    conditions = [
        Account.organization_id == current_user.organization_id,
        Account.is_active.is_(True),
        Account.account_type.in_(inflation_types),
    ]
    if user_id:
        conditions.append(Account.user_id == user_id)

    res = await db.execute(select(Account).where(and_(*conditions)))
    accts = res.scalars().all()

    # Total portfolio for percentage
    all_res = await db.execute(
        select(Account).where(
            and_(
                Account.organization_id == current_user.organization_id,
                Account.is_active.is_(True),
            )
        )
    )
    all_accts = all_res.scalars().all()
    _dash_svc = DashboardService(db)
    total_portfolio = float(sum(
        _dash_svc._calculate_account_value(a)
        for a in all_accts
        if a.account_type.is_asset and _dash_svc._should_include_in_networth(a)
    ))

    account_dicts = [
        {
            "id": str(a.id),
            "name": a.name,
            "account_type": a.account_type.value,
            "current_balance": float(a.current_balance or 0),
            "nominal_return": None,  # could be enriched from holdings if available
        }
        for a in accts
    ]

    result = analyze_inflation_linked_accounts(account_dicts, total_portfolio)

    return InflationTrackingResponse(
        total_inflation_linked=result.total_inflation_linked,
        total_portfolio=result.total_portfolio,
        inflation_linked_pct=result.inflation_linked_pct,
        holdings=[InflationLinkedHoldingResponse(**vars(h)) for h in result.holdings],
        cpi_rate=result.cpi_rate,
        cpi_is_estimated=result.cpi_is_estimated,
        ibond_fixed_rate=result.ibond_fixed_rate,
        ibond_composite_rate=result.ibond_composite_rate,
        ibond_rate_is_stale=result.ibond_rate_is_stale,
        ibond_rate_as_of=result.ibond_rate_as_of,
        generic_real_return=result.generic_real_return,
        data_note=result.data_note,
    )
