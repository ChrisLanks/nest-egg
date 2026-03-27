"""What-If Scenario Modeling API endpoints.

Three stateless calculators:
  C1 — Mortgage Payoff vs Invest
  C2 — State Relocation Tax Impact
  C3 — Job/Salary Change
"""

import math
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.constants.financial import FICA, FIRE, SS, TAX
from app.dependencies import get_current_user
from app.models.user import User
from app.services.state_tax_service import StateTaxService

router = APIRouter()


# ── C1: Mortgage Payoff vs Invest ────────────────────────────────────────────

class MortgageVsInvestRequest(BaseModel):
    remaining_balance: float = Field(..., gt=0)
    interest_rate: float = Field(..., gt=0, description="Annual interest rate as decimal, e.g. 0.065")
    monthly_payment: float = Field(..., gt=0)
    extra_monthly_payment: float = Field(0, ge=0)
    expected_investment_return: float = Field(0.08, description="Expected annual return")
    tax_bracket: float = Field(0.22, description="Marginal tax bracket as decimal")


class MortgageVsInvestResponse(BaseModel):
    pay_off_early: dict
    invest_extra: dict
    breakeven_return: Optional[float]
    recommendation: str


@router.post("/mortgage-vs-invest", response_model=MortgageVsInvestResponse)
async def mortgage_vs_invest(
    request: MortgageVsInvestRequest,
    current_user: User = Depends(get_current_user),
):
    """Compare paying off mortgage early vs investing the extra payment."""
    balance = request.remaining_balance
    monthly_rate = request.interest_rate / 12
    payment = request.monthly_payment
    extra = request.extra_monthly_payment
    inv_return = request.expected_investment_return
    tax_bracket = request.tax_bracket

    # Scenario A: Pay off early (normal payments + extra)
    bal_a = balance
    months_a = 0
    total_interest_a = 0
    while bal_a > 0 and months_a < 600:
        interest = bal_a * monthly_rate
        total_interest_a += interest
        principal = min(payment + extra - interest, bal_a)
        if principal <= 0:
            break
        bal_a -= principal
        months_a += 1

    # Scenario B: Normal payments, invest extra
    bal_b = balance
    months_b = 0
    total_interest_b = 0
    while bal_b > 0 and months_b < 600:
        interest = bal_b * monthly_rate
        total_interest_b += interest
        principal = min(payment - interest, bal_b)
        if principal <= 0:
            break
        bal_b -= principal
        months_b += 1

    interest_saved = total_interest_b - total_interest_a

    # Investment growth of extra payments over original payoff period
    monthly_inv_return = (1 + inv_return) ** (1 / 12) - 1
    portfolio_value = 0
    for m in range(months_b):
        portfolio_value = portfolio_value * (1 + monthly_inv_return) + extra

    # After-tax investment return consideration
    # Mortgage interest is tax-deductible, so effective rate is lower
    effective_mortgage_rate = request.interest_rate * (1 - tax_bracket)

    # Breakeven: what investment return makes investing better?
    if extra > 0 and months_b > 0:
        # The breakeven return is approximately the after-tax mortgage rate
        breakeven = effective_mortgage_rate
    else:
        breakeven = None

    # Recommendation
    if inv_return > effective_mortgage_rate + 0.02:
        recommendation = (
            "Investing the extra payment is likely better — your expected return "
            f"({inv_return*100:.1f}%) exceeds the after-tax mortgage cost "
            f"({effective_mortgage_rate*100:.1f}%) by more than 2%."
        )
    elif inv_return < effective_mortgage_rate:
        recommendation = (
            "Paying off the mortgage early is likely better — your expected return "
            f"({inv_return*100:.1f}%) is below the after-tax mortgage cost "
            f"({effective_mortgage_rate*100:.1f}%)."
        )
    else:
        recommendation = (
            "It's close — the guaranteed savings from early payoff roughly match "
            "expected investment returns. Consider your risk tolerance."
        )

    return MortgageVsInvestResponse(
        pay_off_early={
            "payoff_months": months_a,
            "payoff_years": round(months_a / 12, 1),
            "total_interest_paid": round(total_interest_a, 2),
            "interest_saved": round(interest_saved, 2),
        },
        invest_extra={
            "original_payoff_months": months_b,
            "portfolio_value_at_payoff": round(portfolio_value, 2),
            "total_interest_paid": round(total_interest_b, 2),
        },
        breakeven_return=round(breakeven, 4) if breakeven else None,
        recommendation=recommendation,
    )


# ── C2: State Relocation Tax Impact ─────────────────────────────────────────

class RelocationTaxRequest(BaseModel):
    current_state: str = Field(..., min_length=2, max_length=2)
    target_state: str = Field(..., min_length=2, max_length=2)
    annual_income: float = Field(..., gt=0)
    capital_gains_income: float = Field(0, ge=0)
    retirement_income: float = Field(0, ge=0)


class RelocationTaxResponse(BaseModel):
    current_state_tax: float
    target_state_tax: float
    annual_savings: float
    five_year_savings: float
    considerations: list


# State-specific considerations
_STATE_NOTES = {
    "TX": "No state income tax, but higher property tax rates (avg 1.8%)",
    "FL": "No state income tax; no estate tax",
    "WA": "No income tax, but has capital gains tax on gains >$250K",
    "NV": "No state income tax; lower cost of living in many areas",
    "TN": "No income tax on wages; Hall tax on dividends repealed in 2021",
    "CA": "Highest marginal rate (13.3%); taxes capital gains as ordinary income",
    "NY": "High state + city tax (NYC adds 3-4%); estate tax with $6.94M exemption",
    "NJ": "High income tax (up to 10.75%); high property taxes",
    "IL": "Flat 4.95% income tax; does not tax retirement income",
    "PA": "Flat 3.07% income tax; does not tax most retirement income",
}


@router.post("/relocation-tax", response_model=RelocationTaxResponse)
async def relocation_tax_impact(
    request: RelocationTaxRequest,
    current_user: User = Depends(get_current_user),
):
    """Compare state tax burden between current and target states."""
    total_income = Decimal(str(
        request.annual_income + request.capital_gains_income + request.retirement_income
    ))

    current_tax = StateTaxService.calculate_state_tax(
        request.current_state, total_income
    )
    target_tax = StateTaxService.calculate_state_tax(
        request.target_state, total_income
    )

    annual_savings = float(current_tax - target_tax)

    considerations = []
    for state in [request.current_state.upper(), request.target_state.upper()]:
        note = _STATE_NOTES.get(state)
        if note:
            considerations.append(f"{state}: {note}")

    if annual_savings > 0:
        considerations.append(
            f"Moving to {request.target_state.upper()} could save ~${annual_savings:,.0f}/year in state taxes."
        )
    elif annual_savings < 0:
        considerations.append(
            f"Moving to {request.target_state.upper()} would increase state taxes by ~${abs(annual_savings):,.0f}/year."
        )

    return RelocationTaxResponse(
        current_state_tax=float(current_tax),
        target_state_tax=float(target_tax),
        annual_savings=round(annual_savings, 2),
        five_year_savings=round(annual_savings * 5, 2),
        considerations=considerations,
    )


# ── C3: Job/Salary Change ───────────────────────────────────────────────────

class SalaryChangeRequest(BaseModel):
    current_salary: float = Field(..., gt=0)
    new_salary: float = Field(..., gt=0)
    current_state: str = Field(..., min_length=2, max_length=2)
    new_state: Optional[str] = Field(None, min_length=2, max_length=2)
    filing_status: str = Field("single", description="single or married")
    new_401k_match_pct: float = Field(0, ge=0, le=100, description="Employer 401k match %")
    current_401k_match_pct: float = Field(0, ge=0, le=100)
    hsa_contribution: float = Field(0, ge=0, description="Employer HSA contribution")
    equity_value: float = Field(0, ge=0, description="Annual equity/RSU value")


class SalaryChangeResponse(BaseModel):
    net_take_home_change: float
    retirement_impact_10yr: float
    true_compensation_comparison: dict
    recommendation: str


@router.post("/salary-change", response_model=SalaryChangeResponse)
async def salary_change_comparison(
    request: SalaryChangeRequest,
    current_user: User = Depends(get_current_user),
):
    """Compare total compensation and net impact of a salary change."""
    import datetime
    new_state = request.new_state or request.current_state
    current_year = datetime.date.today().year
    filing_status = request.filing_status

    # Federal tax using year-keyed brackets from constants
    def federal_tax(income: float) -> float:
        tax_data = TAX.for_year(current_year)
        bracket_key = "BRACKETS_MARRIED" if filing_status.lower() in ("married", "mfj") else "BRACKETS_SINGLE"
        brackets = tax_data[bracket_key]
        tax = 0.0
        prev = 0.0
        for rate, ceiling in brackets:
            taxable = min(income, ceiling) - prev
            if taxable > 0:
                tax += taxable * rate
            prev = ceiling
            if income <= ceiling:
                break
        return tax

    current_federal = federal_tax(request.current_salary)
    new_federal = federal_tax(request.new_salary)

    current_state_tax = float(StateTaxService.calculate_state_tax(
        request.current_state, Decimal(str(request.current_salary))
    ))
    new_state_tax = float(StateTaxService.calculate_state_tax(
        new_state, Decimal(str(request.new_salary))
    ))

    # FICA (Social Security 6.2% up to taxable max + Medicare 1.45%)
    ss_taxable_max = SS.TAXABLE_MAX

    def fica(salary):
        ss = min(salary, ss_taxable_max) * float(FICA.SS_EMPLOYEE_RATE)
        medicare = salary * float(FICA.MEDICARE_EMPLOYEE_RATE)
        return ss + medicare

    current_fica = fica(request.current_salary)
    new_fica = fica(request.new_salary)

    current_net = request.current_salary - current_federal - current_state_tax - current_fica
    new_net = request.new_salary - new_federal - new_state_tax - new_fica

    net_change = new_net - current_net

    # Retirement impact: 401k match difference over 10 years at 7% growth
    current_match = request.current_salary * request.current_401k_match_pct / 100
    new_match = request.new_salary * request.new_401k_match_pct / 100
    match_diff_annual = new_match - current_match

    # FV of annual match difference over 10 years at expected return
    if match_diff_annual != 0:
        r = FIRE.DEFAULT_EXPECTED_RETURN
        retirement_impact = match_diff_annual * ((1 + r) ** 10 - 1) / r
    else:
        retirement_impact = 0

    # True compensation comparison
    current_total = (
        request.current_salary
        + current_match
    )
    new_total = (
        request.new_salary
        + new_match
        + request.hsa_contribution
        + request.equity_value
    )

    if net_change > 0:
        recommendation = (
            f"The new position increases your after-tax take-home by ${net_change:,.0f}/year. "
            f"Total compensation (including benefits) goes from ${current_total:,.0f} to ${new_total:,.0f}."
        )
    else:
        recommendation = (
            f"The new position decreases your after-tax take-home by ${abs(net_change):,.0f}/year. "
            "Consider whether non-monetary benefits justify the difference."
        )

    return SalaryChangeResponse(
        net_take_home_change=round(net_change, 2),
        retirement_impact_10yr=round(retirement_impact, 2),
        true_compensation_comparison={
            "current": {
                "gross_salary": request.current_salary,
                "employer_401k_match": round(current_match, 2),
                "total_compensation": round(current_total, 2),
                "net_take_home": round(current_net, 2),
                "federal_tax": round(current_federal, 2),
                "state_tax": round(current_state_tax, 2),
                "fica": round(current_fica, 2),
            },
            "new": {
                "gross_salary": request.new_salary,
                "employer_401k_match": round(new_match, 2),
                "hsa_contribution": request.hsa_contribution,
                "equity_value": request.equity_value,
                "total_compensation": round(new_total, 2),
                "net_take_home": round(new_net, 2),
                "federal_tax": round(new_federal, 2),
                "state_tax": round(new_state_tax, 2),
                "fica": round(new_fica, 2),
            },
        },
        recommendation=recommendation,
    )


# ── C4: Early Retirement / Part-Time ─────────────────────────────────────────

class EarlyRetirementRequest(BaseModel):
    current_age: int = Field(..., ge=18, le=80)
    target_retirement_age: int = Field(..., ge=25, le=80)
    current_savings: float = Field(..., ge=0)
    annual_savings: float = Field(0, ge=0, description="Annual savings contribution")
    annual_expenses: float = Field(..., gt=0)
    expected_return: float = Field(0.07, description="Expected annual return")
    ss_benefit_at_62: float = Field(0, ge=0, description="Estimated SS monthly benefit at 62")


class EarlyRetirementResponse(BaseModel):
    fire_number: float
    gap_to_fire: float
    years_to_fire: Optional[float]
    current_trajectory_age: Optional[int]
    on_track: bool
    projected_at_target: float
    ss_annual_income: float
    recommendation: str


@router.post("/early-retirement", response_model=EarlyRetirementResponse)
async def early_retirement_analysis(
    request: EarlyRetirementRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze early retirement feasibility using the FIRE framework."""
    fire_number = request.annual_expenses * 25  # 4% rule
    gap = max(0, fire_number - request.current_savings)

    # Project savings to target retirement age
    years_to_target = max(0, request.target_retirement_age - request.current_age)
    r = request.expected_return

    # FV of current savings + annual contributions
    fv_current = request.current_savings * (1 + r) ** years_to_target
    if r > 0 and request.annual_savings > 0:
        fv_contributions = request.annual_savings * ((1 + r) ** years_to_target - 1) / r
    else:
        fv_contributions = request.annual_savings * years_to_target
    projected_at_target = fv_current + fv_contributions

    # Years to reach FIRE number
    if request.annual_savings > 0 and r > 0:
        # Solve: current_savings * (1+r)^n + annual_savings * ((1+r)^n - 1)/r = fire_number
        # Binary search for n
        years_to_fire = None
        for n in range(1, 100):
            fv = request.current_savings * (1 + r) ** n + request.annual_savings * ((1 + r) ** n - 1) / r
            if fv >= fire_number:
                years_to_fire = n
                break
        current_trajectory_age = (request.current_age + years_to_fire) if years_to_fire else None
    elif request.annual_savings > 0:
        # Zero return — simple division
        years_needed = gap / request.annual_savings if request.annual_savings > 0 else None
        years_to_fire = math.ceil(years_needed) if years_needed else None
        current_trajectory_age = (request.current_age + years_to_fire) if years_to_fire else None
    else:
        years_to_fire = None
        current_trajectory_age = None

    on_track = projected_at_target >= fire_number

    # SS income (annual, available at 62)
    ss_annual = request.ss_benefit_at_62 * 12

    if on_track:
        recommendation = (
            f"You are on track to reach your FIRE number of ${fire_number:,.0f} "
            f"by age {request.target_retirement_age}. Projected savings: ${projected_at_target:,.0f}."
        )
    elif current_trajectory_age and current_trajectory_age <= request.target_retirement_age + 5:
        recommendation = (
            f"You're close — at the current rate, you'll reach FIRE by age {current_trajectory_age}. "
            f"Increasing savings by ${max(0, (fire_number - projected_at_target) / max(1, years_to_target)):,.0f}/year "
            "could close the gap."
        )
    else:
        recommendation = (
            f"Your FIRE number is ${fire_number:,.0f} but you're projected to have "
            f"${projected_at_target:,.0f} at age {request.target_retirement_age}. "
            "Consider increasing savings or adjusting your target retirement age."
        )

    return EarlyRetirementResponse(
        fire_number=round(fire_number, 2),
        gap_to_fire=round(gap, 2),
        years_to_fire=years_to_fire,
        current_trajectory_age=current_trajectory_age,
        on_track=on_track,
        projected_at_target=round(projected_at_target, 2),
        ss_annual_income=round(ss_annual, 2),
        recommendation=recommendation,
    )
