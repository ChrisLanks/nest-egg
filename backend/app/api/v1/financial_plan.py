"""Unified Financial Plan Summary endpoint.

Aggregates net worth, retirement, education, debt, insurance, estate, and
emergency fund data into a single financial health view with a composite score.
"""

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
from app.constants.financial import EDUCATION, ESTATE, FIRE, HEALTH, RETIREMENT, SAVINGS_GOALS
from app.services.net_worth_service import NetWorthService
from app.services.rate_limit_service import rate_limit_service

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
    http_request: Request,
    user_id: Optional[str] = Query(default=None, description="Household member user ID; defaults to current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a unified financial plan summary with health score and action items."""
    # This endpoint fans out to 7+ services — keep per-user rate modest.
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=10, window_seconds=60, identifier=str(current_user.id)
    )
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
        if not member:
            raise HTTPException(status_code=404, detail="Household member not found")
        subject_user = member

    org_id = current_user.organization_id

    # ── Net Worth ────────────────────────────────────────────────────────
    nw_svc = NetWorthService()
    try:
        nw_data = await nw_svc.get_current_breakdown(db, org_id)
        net_worth_section = {
            "total": nw_data["total_net_worth"],
            "assets": nw_data["total_assets"],
            "liabilities": nw_data["total_liabilities"],
        }
    except Exception:
        logger.exception("financial-plan: net worth section failed")
        net_worth_section = {"total": 0, "assets": 0, "liabilities": 0}

    # ── Retirement ───────────────────────────────────────────────────────
    try:
        retirement_section = await _build_retirement_section(db, org_id, subject_user)
    except Exception:
        logger.exception("financial-plan: retirement section failed")
        retirement_section = {"on_track": False, "no_scenario": True, "projected_at_retirement": 0,
                               "monthly_income_projected": 0, "monthly_income_needed": 0, "gap": 0,
                               "retirement_age": RETIREMENT.DEFAULT_RETIREMENT_AGE, "years_until_retirement": 0}

    # ── Education ────────────────────────────────────────────────────────
    try:
        education_section = await _build_education_section(db, org_id)
    except Exception:
        logger.exception("financial-plan: education section failed")
        education_section = {"total_education_gap": 0, "children": [], "total_529_balance": 0}

    # ── Debt ─────────────────────────────────────────────────────────────
    try:
        debt_section = await _build_debt_section(db, org_id)
    except Exception:
        logger.exception("financial-plan: debt section failed")
        debt_section = {"total_debt": 0, "high_interest_debt": 0, "accounts": []}

    # ── Insurance ────────────────────────────────────────────────────────
    try:
        insurance_section = await _build_insurance_section(db, org_id, nw_data["total_net_worth"])
    except Exception:
        logger.exception("financial-plan: insurance section failed")
        insurance_section = {"life_coverage_gap": 0, "life_coverage_need": 0, "life_coverage_existing": 0,
                              "has_disability": False, "has_umbrella": False, "umbrella_recommended": False,
                              "_has_life": False, "_coverage_score": 0}

    # ── Estate ───────────────────────────────────────────────────────────
    try:
        estate_section = await _build_estate_section(db, org_id, subject_user, nw_data["total_net_worth"])
    except Exception:
        logger.exception("financial-plan: estate section failed")
        estate_section = {"has_will": False, "has_poa": False, "has_hcpoa": False,
                          "has_trust": False, "beneficiary_coverage": 0}

    # ── Emergency Fund ───────────────────────────────────────────────────
    try:
        emergency_section = await _build_emergency_fund_section(db, org_id)
    except Exception:
        logger.exception("financial-plan: emergency fund section failed")
        emergency_section = {"months_covered": 0, "recommended_months": HEALTH.EMERGENCY_FUND_TARGET_MONTHS, "shortfall": 0}

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
        "no_scenario" if retirement_section.get("no_scenario")
        else "on_track" if retirement_section.get("on_track")
        else "critical" if retirement_section.get("gap", 0) > HEALTH.RETIREMENT_GAP_CRITICAL
        else "needs_attention"
    )
    education_section["status"] = (
        "on_track" if education_section.get("total_education_gap", 0) == 0
        else "needs_attention"
    )
    debt_section["status"] = (
        "on_track" if debt_section.get("high_interest_debt", 0) == 0
        else "critical" if debt_section.get("high_interest_debt", 0) > HEALTH.DEBT_HIGH_INTEREST_CRITICAL
        else "needs_attention"
    )
    insurance_section["status"] = (
        "on_track" if insurance_section.get("_coverage_score", 0) >= HEALTH.INSURANCE_SCORE_GOOD
        else "critical" if insurance_section.get("_coverage_score", 0) < HEALTH.INSURANCE_SCORE_CRITICAL
        else "needs_attention"
    )
    estate_section["status"] = (
        "on_track" if estate_section.get("has_will") and estate_section.get("has_poa")
        else "critical" if not estate_section.get("has_will")
        else "needs_attention"
    )
    emergency_section["status"] = (
        "on_track" if emergency_section.get("months_covered", 0) >= HEALTH.EMERGENCY_FUND_TARGET_MONTHS
        else "critical" if emergency_section.get("months_covered", 0) < HEALTH.EMERGENCY_FUND_CRITICAL_MONTHS
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
            "retirement_age": RETIREMENT.DEFAULT_RETIREMENT_AGE,
            "years_until_retirement": 0,
            "no_scenario": True,
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
    # Projected monthly income from portfolio using the configured safe withdrawal rate
    monthly_income = projected * FIRE.DEFAULT_WITHDRAWAL_RATE / 12 if projected > 0 else 0
    success_rate = float(sim.success_rate) if sim else 0
    on_track = success_rate >= FIRE.MC_ON_TRACK_SUCCESS_RATE

    return {
        "on_track": on_track,
        "projected_at_retirement": round(projected),
        "monthly_income_projected": round(monthly_income),
        "monthly_income_needed": round(monthly_spending),
        "gap": round(max(0, monthly_spending - monthly_income)),
        "retirement_age": scenario.retirement_age,
        "years_until_retirement": years_until,
        "success_rate": round(success_rate, 1),
        "no_scenario": False,
    }


async def _build_education_section(db: AsyncSession, org_id) -> dict:
    """Summarize education planning from dependents, crediting existing 529 balances."""
    result = await db.execute(
        select(Dependent).where(Dependent.household_id == org_id)
    )
    dependents = result.scalars().all()

    # Sum all active 529 account balances for this household
    from app.models.account import AccountType as _AccountType
    savings_result = await db.execute(
        select(func.coalesce(func.sum(Account.current_balance), 0)).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type == _AccountType.RETIREMENT_529,
                Account.is_active.is_(True),  # noqa: E712
            )
        )
    )
    total_529_balance = float(savings_result.scalar() or 0)

    children = []
    total_projected_cost = 0
    import datetime as _dt
    current_year = _dt.date.today().year
    college_years = EDUCATION.COLLEGE_YEARS
    inflation = EDUCATION.COLLEGE_INFLATION_RATE

    for dep in dependents:
        start_year = getattr(dep, "expected_college_start_year", None) or (current_year + 10)
        years_until = max(0, start_year - current_year)
        # Use year-keyed cost data, projected to enrollment year
        projected_costs = EDUCATION.costs_for_year(start_year)
        annual_cost = projected_costs.get("public_in_state", 23_250)
        projected_total = round(annual_cost * college_years)
        children.append({
            "name": dep.first_name if hasattr(dep, 'first_name') else str(dep.id)[:8],
            "start_year": start_year,
            "projected_total_cost": projected_total,
        })
        total_projected_cost += projected_total

    # Offset projected cost by existing 529 savings (529 balance also grows, but conservative)
    total_gap = max(0, total_projected_cost - total_529_balance)

    return {
        "total_children": len(children),
        "total_education_gap": round(total_gap),
        "total_projected_cost": round(total_projected_cost),
        "total_529_balance": round(total_529_balance),
        "children": children,
    }


async def _build_debt_section(db: AsyncSession, org_id) -> dict:
    """Summarize debt from accounts.

    Monthly payment estimates use actual transaction data (payments made to debt
    accounts in the last 90 days) where available, falling back to account-level
    ``monthly_payment`` field, then a computed amortization estimate.
    """
    debt_types = [AccountType.CREDIT_CARD, AccountType.LOAN,
                  AccountType.STUDENT_LOAN, AccountType.MORTGAGE]
    result = await db.execute(
        select(Account).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_(debt_types),
                Account.is_active.is_(True),  # noqa: E712
            )
        )
    )
    debt_accounts = result.scalars().all()

    # Look up recent actual payments: positive transactions on debt accounts
    # (deposits/credits on a debt account = payments made)
    import datetime as _dtm
    from app.models.transaction import Transaction as _Transaction
    _90d_ago = _dtm.date.today() - _dtm.timedelta(days=90)
    debt_account_ids = [acct.id for acct in debt_accounts]

    actual_payments: dict = {}
    if debt_account_ids:
        payment_result = await db.execute(
            select(
                _Transaction.account_id,
                func.avg(func.abs(_Transaction.amount)).label("avg_monthly"),
            ).where(
                and_(
                    _Transaction.account_id.in_(debt_account_ids),
                    _Transaction.date >= _90d_ago,
                    _Transaction.amount > 0,  # positive = payment on a debt account
                    _Transaction.is_transfer.is_(False),
                )
            ).group_by(_Transaction.account_id)
        )
        for row in payment_result:
            actual_payments[row.account_id] = float(row.avg_monthly or 0)

    total_debt = Decimal("0")
    high_interest = Decimal("0")
    monthly_payments = Decimal("0")
    mortgage_payoff = None

    for acct in debt_accounts:
        balance = abs(acct.current_balance or Decimal("0"))
        total_debt += balance

        # Credit card = high interest (any credit card balance triggers this)
        if acct.account_type == AccountType.CREDIT_CARD:
            high_interest += balance

        if acct.account_type == AccountType.MORTGAGE:
            import math as _math
            rate = float(getattr(acct, 'interest_rate', None) or 0)
            # Prefer: account-level monthly_payment → actual transactions → amortization
            monthly_pmt = float(getattr(acct, 'monthly_payment', None) or 0)
            if not monthly_pmt:
                monthly_pmt = actual_payments.get(acct.id, 0)
            if rate > 0 and monthly_pmt > 0 and float(balance) > 0:
                monthly_rate = rate / 100 / 12
                ratio = monthly_rate * float(balance) / monthly_pmt
                if ratio < 1:
                    years_left = (-_math.log(1 - ratio) / _math.log(1 + monthly_rate)) / 12
                    mortgage_payoff = _dtm.date.today().year + int(_math.ceil(years_left))
                else:
                    mortgage_payoff = _dtm.date.today().year + 30
                monthly_payments += Decimal(str(monthly_pmt))
            elif monthly_pmt > 0:
                monthly_payments += Decimal(str(monthly_pmt))
                if mortgage_payoff is None:
                    mortgage_payoff = _dtm.date.today().year + 30
            else:
                # Fallback: 30-year amortization
                monthly_payments += balance / 360
                if mortgage_payoff is None:
                    mortgage_payoff = _dtm.date.today().year + 30
        else:
            # Prefer actual transaction data, then account monthly_payment, then estimate
            pmt = actual_payments.get(acct.id, 0)
            if not pmt:
                pmt = float(getattr(acct, 'monthly_payment', None) or 0)
            if not pmt and float(balance) > 0:
                # Fallback: estimate based on typical minimum payment (2% of balance or $25)
                from app.constants.financial import DEBT as _DEBT
                pmt = max(25.0, float(balance) * _DEBT.MIN_PAYMENT_RATE)
            monthly_payments += Decimal(str(pmt))

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
                InsurancePolicy.is_active.is_(True),  # noqa: E712
            )
        )
    )
    policies = result.scalars().all()

    policy_types = {p.policy_type for p in policies}

    has_life = any(t in policy_types for t in [PolicyType.TERM_LIFE, PolicyType.WHOLE_LIFE, PolicyType.UNIVERSAL_LIFE])
    has_disability = any(t in policy_types for t in [PolicyType.DISABILITY_SHORT_TERM, PolicyType.DISABILITY_LONG_TERM])
    has_umbrella = PolicyType.UMBRELLA in policy_types
    umbrella_recommended = net_worth > HEALTH.UMBRELLA_RECOMMEND_NET_WORTH

    # Estimate life coverage gap (10x annual income - existing coverage)
    total_life_coverage = sum(
        float(p.coverage_amount or 0)
        for p in policies
        if p.policy_type in [PolicyType.TERM_LIFE, PolicyType.WHOLE_LIFE, PolicyType.UNIVERSAL_LIFE]
    )

    # Estimate gross annual income from YTD transaction income (last 12 months)
    import datetime as _dtins
    _12m_ago = _dtins.date.today() - _dtins.timedelta(days=365)
    from app.models.transaction import Transaction as _TxIns
    income_result = await db.execute(
        select(func.coalesce(func.sum(_TxIns.amount), 0)).join(
            Account, _TxIns.account_id == Account.id
        ).where(
            and_(
                Account.organization_id == org_id,
                Account.is_active.is_(True),  # noqa: E712
                _TxIns.date >= _12m_ago,
                _TxIns.amount > 0,  # income = positive transaction
                _TxIns.is_transfer.is_(False),
            )
        )
    )
    annual_income = float(income_result.scalar() or 0)

    if annual_income > 0:
        estimated_need = round(annual_income * HEALTH.LIFE_INSURANCE_INCOME_MULTIPLE)
    else:
        # Fallback when no income data is available — use conservative constant, not $1M
        estimated_need = HEALTH.LIFE_INSURANCE_FALLBACK_NEED
    life_gap = max(0, estimated_need - total_life_coverage)

    return {
        "life_coverage_gap": life_gap,
        "life_coverage_need": estimated_need,
        "life_coverage_existing": round(total_life_coverage),
        "income_used_for_estimate": round(annual_income),
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
                Account.is_active.is_(True),  # noqa: E712
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
                Account.is_active.is_(True),  # noqa: E712
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
    recommended_months = HEALTH.EMERGENCY_FUND_TARGET_MONTHS
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
    """Compute weighted 0-100 financial health score.

    Weights: Retirement 30pts, Emergency Fund 20pts, Insurance 20pts,
             Debt 15pts, Estate 15pts.
    Thresholds sourced from HEALTH constants.
    """
    score = 0

    # Retirement (30 points) — 0 for no scenario, 15 for any projection, 30 if on track
    if retirement.get("on_track"):
        score += 30
    elif not retirement.get("no_scenario") and retirement.get("projected_at_retirement", 0) > 0:
        score += 15

    # Emergency fund (20 points)
    months = emergency.get("months_covered", 0)
    if months >= HEALTH.EMERGENCY_FUND_TARGET_MONTHS:
        score += 20
    elif months >= HEALTH.EMERGENCY_FUND_GOOD:
        score += 12
    elif months >= HEALTH.EMERGENCY_FUND_CRITICAL_MONTHS:
        score += 5

    # Insurance (20 points)
    ins_score = insurance.get("_coverage_score", 0)
    score += int(ins_score * 20 / 100)

    # Debt management (15 points)
    high_interest = debt.get("high_interest_debt", 0)
    if high_interest == 0:
        score += 15
    elif high_interest < HEALTH.DEBT_HIGH_INTEREST_MODERATE:
        score += 10
    elif high_interest < HEALTH.DEBT_HIGH_INTEREST_CRITICAL:
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
    """Generate prioritized action items with navigation links.

    Each action is a dict with:
      - message: human-readable text
      - href: frontend route to resolve the issue
      - priority: "critical" | "important" | "suggestion"
    """
    actions = []

    if not estate.get("has_will"):
        actions.append({
            "message": "Create a will — estate planning is incomplete without one",
            "href": "/life-planning?tab=estate",
            "priority": "critical",
        })

    if insurance.get("umbrella_recommended") and not insurance.get("has_umbrella"):
        threshold = HEALTH.UMBRELLA_RECOMMEND_NET_WORTH
        actions.append({
            "message": f"Add umbrella insurance — net worth exceeds ${threshold:,.0f}",
            "href": "/life-planning?tab=insurance",
            "priority": "important",
        })

    shortfall = emergency.get("shortfall", 0)
    if shortfall > 0:
        months = HEALTH.EMERGENCY_FUND_TARGET_MONTHS
        actions.append({
            "message": f"Increase emergency fund by ${shortfall:,.0f} to reach {months}-month target",
            "href": "/financial-health?tab=liquidity",
            "priority": "critical" if emergency.get("months_covered", 0) < 1 else "important",
        })

    if retirement.get("no_scenario"):
        actions.append({
            "message": "Create a retirement scenario to see if you're on track",
            "href": "/retirement",
            "priority": "important",
        })
    elif not retirement.get("on_track"):
        gap = retirement.get("gap", 0)
        actions.append({
            "message": f"Review retirement plan — projected ${gap:,.0f}/month shortfall",
            "href": "/retirement",
            "priority": "critical" if gap > HEALTH.RETIREMENT_GAP_CRITICAL else "important",
        })

    high_interest = debt.get("high_interest_debt", 0)
    if high_interest > 0:
        actions.append({
            "message": f"Pay down ${high_interest:,.0f} in high-interest credit card debt",
            "href": "/debt-payoff",
            "priority": "critical" if high_interest > HEALTH.DEBT_HIGH_INTEREST_CRITICAL else "important",
        })

    if not insurance.get("_has_life", True):
        need = insurance.get("life_coverage_need", HEALTH.LIFE_INSURANCE_FALLBACK_NEED)
        actions.append({
            "message": f"Consider term life insurance — estimated need ${need:,.0f}",
            "href": "/life-planning?tab=insurance",
            "priority": "important",
        })

    if not insurance.get("has_disability"):
        actions.append({
            "message": "Evaluate disability insurance — protects your income if you can't work",
            "href": "/life-planning?tab=insurance",
            "priority": "important",
        })

    if not estate.get("has_poa"):
        actions.append({
            "message": "Set up a power of attorney for financial and healthcare decisions",
            "href": "/life-planning?tab=estate",
            "priority": "important",
        })

    gap = education.get("total_education_gap", 0)
    if gap > 0:
        existing = education.get("total_529_balance", 0)
        msg = f"Address ${gap:,.0f} education funding gap"
        if existing > 0:
            msg += f" (${existing:,.0f} in 529 already saved)"
        actions.append({
            "message": msg,
            "href": "/education",
            "priority": "suggestion",
        })

    # Sort by priority: critical > important > suggestion, then return top 5
    _priority_order = {"critical": 0, "important": 1, "suggestion": 2}
    actions.sort(key=lambda a: _priority_order.get(a["priority"], 99))
    return actions[:5]
