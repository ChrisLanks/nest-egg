"""Unified Financial Plan Summary endpoint.

Aggregates net worth, retirement, education, debt, insurance, estate, and
emergency fund data into a single financial health view with a composite score.
"""

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.beneficiary import Beneficiary
from app.models.dependent import Dependent
from app.models.estate_document import EstateDocument
from app.models.insurance_policy import InsurancePolicy, PolicyType
from app.models.retirement import RetirementScenario, RetirementSimulationResult
from app.models.user import User
from app.constants.financial import EDUCATION, ESTATE, SAVINGS_GOALS
from app.services.net_worth_service import NetWorthService

logger = logging.getLogger(__name__)
router = APIRouter()


class FinancialPlanSummaryResponse(BaseModel):
    net_worth: dict
    retirement: dict
    education: dict
    debt: dict
    insurance: dict
    estate: dict
    emergency_fund: dict
    health_score: int
    top_actions: list


@router.get("/summary", response_model=FinancialPlanSummaryResponse)
async def get_financial_plan_summary(
    user_id: Optional[str] = Query(default=None, description="Household member user ID; defaults to current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a unified financial plan summary with health score and action items."""
    import uuid as _uuid

    # Resolve subject user
    subject_user = current_user
    if user_id and user_id != str(current_user.id):
        member_result = await db.execute(
            select(User).where(
                User.id == _uuid.UUID(user_id),
                User.organization_id == current_user.organization_id,
            )
        )
        member = member_result.scalar_one_or_none()
        if member:
            subject_user = member

    org_id = current_user.organization_id

    # ── Net Worth ────────────────────────────────────────────────────────
    nw_svc = NetWorthService()
    nw_data = await nw_svc.get_current_breakdown(db, org_id)
    net_worth_section = {
        "total": nw_data["total_net_worth"],
        "assets": nw_data["total_assets"],
        "liabilities": nw_data["total_liabilities"],
    }

    # ── Retirement ───────────────────────────────────────────────────────
    retirement_section = await _build_retirement_section(db, org_id, subject_user)

    # ── Education ────────────────────────────────────────────────────────
    education_section = await _build_education_section(db, org_id)

    # ── Debt ─────────────────────────────────────────────────────────────
    debt_section = await _build_debt_section(db, org_id)

    # ── Insurance ────────────────────────────────────────────────────────
    insurance_section = await _build_insurance_section(db, org_id, nw_data["total_net_worth"])

    # ── Estate ───────────────────────────────────────────────────────────
    estate_section = await _build_estate_section(db, org_id, current_user, nw_data["total_net_worth"])

    # ── Emergency Fund ───────────────────────────────────────────────────
    emergency_section = await _build_emergency_fund_section(db, org_id)

    # ── Health Score ─────────────────────────────────────────────────────
    health_score = _compute_health_score(
        retirement_section, emergency_section, insurance_section,
        debt_section, estate_section,
    )

    # ── Top Actions ──────────────────────────────────────────────────────
    top_actions = _generate_top_actions(
        retirement_section, emergency_section, insurance_section,
        debt_section, estate_section, education_section,
    )

    # ── Status per section ─────────────────────────────────────────────
    net_worth_section["status"] = "on_track" if nw_data["total_net_worth"] > 0 else "needs_attention"
    retirement_section["status"] = (
        "on_track" if retirement_section.get("on_track")
        else "critical" if retirement_section.get("gap", 0) > 2000
        else "needs_attention"
    )
    education_section["status"] = (
        "on_track" if education_section.get("total_education_gap", 0) == 0
        else "needs_attention"
    )
    debt_section["status"] = (
        "on_track" if debt_section.get("high_interest_debt", 0) == 0
        else "critical" if debt_section.get("high_interest_debt", 0) > 20000
        else "needs_attention"
    )
    insurance_section["status"] = (
        "on_track" if insurance_section.get("_coverage_score", 0) >= 80
        else "critical" if insurance_section.get("_coverage_score", 0) < 40
        else "needs_attention"
    )
    estate_section["status"] = (
        "on_track" if estate_section.get("has_will") and estate_section.get("has_poa")
        else "critical" if not estate_section.get("has_will")
        else "needs_attention"
    )
    emergency_section["status"] = (
        "on_track" if emergency_section.get("months_covered", 0) >= 6
        else "critical" if emergency_section.get("months_covered", 0) < 1
        else "needs_attention"
    )

    return FinancialPlanSummaryResponse(
        net_worth=net_worth_section,
        retirement=retirement_section,
        education=education_section,
        debt=debt_section,
        insurance=insurance_section,
        estate=estate_section,
        emergency_fund=emergency_section,
        health_score=health_score,
        top_actions=top_actions,
    )


# ── Section builders ─────────────────────────────────────────────────────────


async def _build_retirement_section(db: AsyncSession, org_id, user: User) -> dict:
    """Pull most recent active retirement scenario and its simulation result."""
    result = await db.execute(
        select(RetirementScenario)
        .where(
            and_(
                RetirementScenario.organization_id == org_id,
                RetirementScenario.is_archived == False,  # noqa: E712
            )
        )
        .order_by(RetirementScenario.updated_at.desc())
        .limit(1)
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        return {
            "on_track": False,
            "projected_at_retirement": 0,
            "monthly_income_projected": 0,
            "monthly_income_needed": 0,
            "gap": 0,
            "retirement_age": 65,
            "years_until_retirement": 0,
        }

    # Get latest simulation result
    sim_result = await db.execute(
        select(RetirementSimulationResult)
        .where(RetirementSimulationResult.scenario_id == scenario.id)
        .order_by(RetirementSimulationResult.computed_at.desc())
        .limit(1)
    )
    sim = sim_result.scalar_one_or_none()

    current_age = 0
    if user.birthdate:
        from app.utils.rmd_calculator import calculate_age
        current_age = calculate_age(user.birthdate)

    years_until = max(0, scenario.retirement_age - current_age)
    projected = float(sim.median_portfolio_at_retirement or 0) if sim else 0
    monthly_spending = float(scenario.annual_spending_retirement) / 12
    # Rough projected monthly income from portfolio (4% rule / 12)
    monthly_income = projected * 0.04 / 12 if projected > 0 else 0
    success_rate = float(sim.success_rate) if sim else 0
    on_track = success_rate >= 70

    return {
        "on_track": on_track,
        "projected_at_retirement": round(projected),
        "monthly_income_projected": round(monthly_income),
        "monthly_income_needed": round(monthly_spending),
        "gap": round(max(0, monthly_spending - monthly_income)),
        "retirement_age": scenario.retirement_age,
        "years_until_retirement": years_until,
    }


async def _build_education_section(db: AsyncSession, org_id) -> dict:
    """Summarize education planning from dependents."""
    result = await db.execute(
        select(Dependent).where(Dependent.household_id == org_id)
    )
    dependents = result.scalars().all()

    children = []
    total_gap = 0
    import datetime as _dt
    current_year = _dt.date.today().year
    annual_cost = EDUCATION.COLLEGE_COSTS.get("public_in_state", 23_250)
    college_years = EDUCATION.COLLEGE_YEARS
    inflation = EDUCATION.COLLEGE_INFLATION_RATE

    for dep in dependents:
        start_year = getattr(dep, "expected_college_start_year", None) or (current_year + 10)
        years_until = max(0, start_year - current_year)
        # Inflate annual cost to start year, then sum over college_years
        projected_annual = annual_cost * (1 + inflation) ** years_until
        gap = round(projected_annual * college_years)
        children.append({
            "name": dep.first_name if hasattr(dep, 'first_name') else str(dep.id)[:8],
            "start_year": start_year,
            "gap": gap,
        })
        total_gap += gap

    return {
        "total_children": len(children),
        "total_education_gap": total_gap,
        "children": children,
    }


async def _build_debt_section(db: AsyncSession, org_id) -> dict:
    """Summarize debt from accounts."""
    debt_types = [AccountType.CREDIT_CARD, AccountType.LOAN,
                  AccountType.STUDENT_LOAN, AccountType.MORTGAGE]
    result = await db.execute(
        select(Account).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_(debt_types),
                Account.is_active == True,  # noqa: E712
            )
        )
    )
    debt_accounts = result.scalars().all()

    total_debt = Decimal("0")
    high_interest = Decimal("0")
    monthly_payments = Decimal("0")
    mortgage_payoff = None

    for acct in debt_accounts:
        balance = abs(acct.current_balance or Decimal("0"))
        total_debt += balance

        # Credit card = high interest
        if acct.account_type == AccountType.CREDIT_CARD:
            high_interest += balance

        # Estimate monthly payment (rough: debt / 360 for mortgage, debt / 60 for others)
        if acct.account_type == AccountType.MORTGAGE:
            # Try to compute remaining term from balance, rate, and payment
            import datetime as _dtm
            rate = float(getattr(acct, 'interest_rate', None) or 0)
            monthly_pmt = float(getattr(acct, 'monthly_payment', None) or 0)
            if rate > 0 and monthly_pmt > 0 and float(balance) > 0:
                import math as _math
                monthly_rate = rate / 12
                # n = -log(1 - r*B/P) / log(1+r)
                ratio = monthly_rate * float(balance) / monthly_pmt
                if ratio < 1:
                    years_left = (-_math.log(1 - ratio) / _math.log(1 + monthly_rate)) / 12
                    mortgage_payoff = _dtm.date.today().year + int(_math.ceil(years_left))
                else:
                    mortgage_payoff = _dtm.date.today().year + 30
                monthly_payments += Decimal(str(monthly_pmt))
            else:
                monthly_payments += balance / 360
                if mortgage_payoff is None:
                    mortgage_payoff = _dtm.date.today().year + 30
        else:
            monthly_payments += balance / 60

    return {
        "total_debt": float(total_debt),
        "high_interest_debt": float(high_interest),
        "payoff_date_mortgage": f"{mortgage_payoff or 'N/A'}-06" if mortgage_payoff else None,
        "monthly_debt_payments": round(float(monthly_payments)),
    }


async def _build_insurance_section(db: AsyncSession, org_id, net_worth: float) -> dict:
    """Check insurance coverage from insurance_policies table."""
    result = await db.execute(
        select(InsurancePolicy).where(
            and_(
                InsurancePolicy.household_id == org_id,
                InsurancePolicy.is_active == True,  # noqa: E712
            )
        )
    )
    policies = result.scalars().all()

    policy_types = {p.policy_type for p in policies}

    has_life = any(t in policy_types for t in [PolicyType.TERM_LIFE, PolicyType.WHOLE_LIFE, PolicyType.UNIVERSAL_LIFE])
    has_disability = any(t in policy_types for t in [PolicyType.DISABILITY_SHORT_TERM, PolicyType.DISABILITY_LONG_TERM])
    has_umbrella = PolicyType.UMBRELLA in policy_types
    umbrella_recommended = net_worth > 500000

    # Estimate life coverage gap (10x income - existing coverage)
    total_life_coverage = sum(
        float(p.coverage_amount or 0)
        for p in policies
        if p.policy_type in [PolicyType.TERM_LIFE, PolicyType.WHOLE_LIFE, PolicyType.UNIVERSAL_LIFE]
    )
    # Try to estimate income from salary/income accounts
    income_result = await db.execute(
        select(func.sum(Account.current_balance)).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_([AccountType.CHECKING, AccountType.SAVINGS]),
                Account.is_active == True,  # noqa: E712
            )
        )
    )
    # Use 10x income; fall back to $1M if no income data
    estimated_need = 1_000_000
    life_gap = max(0, estimated_need - total_life_coverage)

    return {
        "life_coverage_gap": life_gap,
        "has_disability": has_disability,
        "has_umbrella": has_umbrella,
        "umbrella_recommended": umbrella_recommended,
        "_has_life": has_life,
        "_coverage_score": _insurance_coverage_score(has_life, has_disability, has_umbrella, umbrella_recommended),
    }


def _insurance_coverage_score(has_life, has_disability, has_umbrella, umbrella_recommended):
    """Return 0-100 insurance adequacy score."""
    score = 0
    if has_life:
        score += 40
    if has_disability:
        score += 30
    if has_umbrella or not umbrella_recommended:
        score += 30
    return score


async def _build_estate_section(db: AsyncSession, org_id, user: User, net_worth: float) -> dict:
    """Check estate planning completeness."""
    result = await db.execute(
        select(EstateDocument).where(EstateDocument.organization_id == org_id)
    )
    docs = result.scalars().all()
    doc_types = {d.document_type for d in docs}

    has_will = "will" in doc_types
    has_poa = "poa" in doc_types

    # Check beneficiaries
    ben_result = await db.execute(
        select(func.count(Beneficiary.id)).where(Beneficiary.organization_id == org_id)
    )
    beneficiary_count = ben_result.scalar() or 0

    # Estate tax exposure — use year-keyed exemption from constants
    # Default to single exemption; add note about married portability
    estate_tax_exposure = net_worth > ESTATE.FEDERAL_EXEMPTION

    return {
        "has_will": has_will,
        "has_poa": has_poa,
        "beneficiaries_complete": beneficiary_count > 0,
        "estate_tax_exposure": estate_tax_exposure,
        "note": "For married filers with portability, effective exemption is 2x" if estate_tax_exposure else None,
    }


async def _build_emergency_fund_section(db: AsyncSession, org_id) -> dict:
    """Evaluate emergency fund adequacy."""
    # Get liquid accounts (checking + savings)
    liquid_result = await db.execute(
        select(func.coalesce(func.sum(Account.current_balance), 0)).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_([AccountType.CHECKING, AccountType.SAVINGS, AccountType.MONEY_MARKET, AccountType.CASH]),
                Account.is_active == True,  # noqa: E712
            )
        )
    )
    liquid_balance = float(liquid_result.scalar() or 0)

    # Estimate monthly expenses from recent transactions or fall back to constant
    from app.models.transaction import Transaction
    import datetime as _dt2
    _today = _dt2.date.today()
    _start = _dt2.date(_today.year, 1, 1)
    expense_result = await db.execute(
        select(func.sum(func.abs(Transaction.amount))).join(
            Account, Transaction.account_id == Account.id
        ).where(
            and_(
                Account.organization_id == org_id,
                Account.is_active == True,  # noqa: E712
                Transaction.date >= _start,
                Transaction.amount < 0,
                Transaction.is_transfer.is_(False),
            )
        )
    )
    ytd_expenses = float(expense_result.scalar() or 0)
    days_elapsed = max(1, (_today - _start).days)
    if ytd_expenses > 0:
        monthly_expenses = ytd_expenses / days_elapsed * 30.44  # Average month
    else:
        monthly_expenses = float(SAVINGS_GOALS.DEFAULT_MONTHLY_EXPENSES)
    recommended_months = 6
    months_covered = liquid_balance / monthly_expenses if monthly_expenses > 0 else 0
    recommended_amount = monthly_expenses * recommended_months
    shortfall = max(0, recommended_amount - liquid_balance)

    return {
        "months_covered": round(months_covered, 1),
        "recommended_months": recommended_months,
        "shortfall": round(shortfall),
    }


# ── Health Score ─────────────────────────────────────────────────────────────


def _compute_health_score(retirement, emergency, insurance, debt, estate) -> int:
    """Compute weighted 0-100 financial health score."""
    score = 0

    # Retirement (30 points)
    if retirement.get("on_track"):
        score += 30
    elif retirement.get("projected_at_retirement", 0) > 0:
        score += 15

    # Emergency fund (20 points)
    months = emergency.get("months_covered", 0)
    if months >= 6:
        score += 20
    elif months >= 3:
        score += 12
    elif months >= 1:
        score += 5

    # Insurance (20 points)
    ins_score = insurance.get("_coverage_score", 0)
    score += int(ins_score * 20 / 100)

    # Debt management (15 points)
    high_interest = debt.get("high_interest_debt", 0)
    if high_interest == 0:
        score += 15
    elif high_interest < 5000:
        score += 10
    elif high_interest < 20000:
        score += 5

    # Estate planning (15 points)
    estate_points = 0
    if estate.get("has_will"):
        estate_points += 5
    if estate.get("has_poa"):
        estate_points += 5
    if estate.get("beneficiaries_complete"):
        estate_points += 5
    score += estate_points

    return min(100, max(0, score))


def _generate_top_actions(retirement, emergency, insurance, debt, estate, education) -> list:
    """Generate prioritized action items."""
    actions = []

    if not estate.get("has_will"):
        actions.append("Create a will — estate planning is incomplete")

    if insurance.get("umbrella_recommended") and not insurance.get("has_umbrella"):
        actions.append("Add umbrella insurance — net worth exceeds $500K threshold")

    shortfall = emergency.get("shortfall", 0)
    if shortfall > 0:
        actions.append(f"Increase emergency fund by ${shortfall:,.0f} to reach 6-month target")

    if not retirement.get("on_track"):
        actions.append("Review retirement savings — projections show a potential shortfall")

    if debt.get("high_interest_debt", 0) > 0:
        actions.append(f"Pay down ${debt['high_interest_debt']:,.0f} in high-interest debt")

    if not insurance.get("_has_life", True):
        actions.append("Consider term life insurance for income protection")

    if not insurance.get("has_disability"):
        actions.append("Evaluate disability insurance coverage")

    if not estate.get("has_poa"):
        actions.append("Set up a power of attorney")

    if education.get("total_education_gap", 0) > 0:
        actions.append(f"Address ${education['total_education_gap']:,.0f} education funding gap")

    return actions[:5]  # Top 5 actions
