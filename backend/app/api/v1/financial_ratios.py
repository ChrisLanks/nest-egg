"""Financial ratios API endpoint — DTI, savings rate, emergency fund, housing ratio."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.services.rate_limit_service import rate_limit_service
from app.models.account import Account, AccountType
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.user import User



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(dependencies=[Depends(_rate_limit)])


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class RatioMetric(BaseModel):
    name: str
    value: Optional[float]
    formatted: str
    grade: str  # "A", "B", "C", "D", "F"
    grade_color: str  # "green", "yellow", "orange", "red"
    threshold_excellent: str
    threshold_good: str
    description: str


class FinancialRatiosResponse(BaseModel):
    metrics: List[RatioMetric]
    overall_grade: str
    overall_score: float  # 0-100
    net_worth: float
    liquid_assets: float
    total_debt: float
    income_provided: bool
    spending_provided: bool
    tips: List[str]


# ---------------------------------------------------------------------------
# Grading helpers
# ---------------------------------------------------------------------------

_GRADE_POINTS = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
_GRADE_COLORS = {"A": "green", "B": "green", "C": "yellow", "D": "orange", "F": "red"}
_SCORE_FROM_GRADE = {"A": 95, "B": 80, "C": 65, "D": 45, "F": 20}


def _grade_savings_rate(rate: Optional[float]) -> str:
    if rate is None:
        return "F"
    if rate >= 0.20:
        return "A"
    if rate >= 0.10:
        return "B"
    if rate >= 0.05:
        return "C"
    if rate >= 0.0:
        return "D"
    return "F"


def _grade_dti(dti: Optional[float]) -> str:
    if dti is None:
        return "F"
    if dti <= 0.15:
        return "A"
    if dti <= 0.28:
        return "B"
    if dti <= 0.35:
        return "C"
    if dti <= 0.50:
        return "D"
    return "F"


def _grade_emergency_fund(months: Optional[float]) -> str:
    if months is None:
        return "F"
    if months >= 6:
        return "A"
    if months >= 3:
        return "B"
    if months >= 1:
        return "C"
    if months >= 0.5:
        return "D"
    return "F"


def _grade_housing_ratio(ratio: Optional[float]) -> str:
    if ratio is None:
        return "F"
    if ratio <= 0.25:
        return "A"
    if ratio <= 0.30:
        return "B"
    if ratio <= 0.35:
        return "C"
    if ratio <= 0.40:
        return "D"
    return "F"


def _overall_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"


def _make_metric(
    name: str,
    value: Optional[float],
    formatted: str,
    grade: str,
    threshold_excellent: str,
    threshold_good: str,
    description: str,
) -> RatioMetric:
    return RatioMetric(
        name=name,
        value=value,
        formatted=formatted,
        grade=grade,
        grade_color=_GRADE_COLORS[grade],
        threshold_excellent=threshold_excellent,
        threshold_good=threshold_good,
        description=description,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

_DEBT_TYPES = [
    AccountType.CREDIT_CARD.value,
    AccountType.LOAN.value,
    AccountType.MORTGAGE.value,
    AccountType.STUDENT_LOAN.value,
]

_LIQUID_TYPES = [
    AccountType.CHECKING.value,
    AccountType.SAVINGS.value,
    AccountType.MONEY_MARKET.value,
]

_MORTGAGE_TYPES = [AccountType.MORTGAGE.value]


@router.get("/financial-ratios", response_model=FinancialRatiosResponse)
async def get_financial_ratios(
    monthly_income: Optional[float] = Query(
        None, description="Gross monthly income (user-provided)"
    ),
    monthly_spending: Optional[float] = Query(
        None, description="Average monthly spending (user-provided)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute DTI, savings rate, emergency fund coverage, housing ratio, and overall
    financial health grade.

    Pass monthly_income and monthly_spending as query params for the most accurate
    results; without them, income-dependent metrics will be skipped.
    """
    org_id = current_user.organization_id

    # ── Latest household net-worth snapshot ──────────────────────────────────
    snapshot_result = await db.execute(
        select(NetWorthSnapshot)
        .where(
            and_(
                NetWorthSnapshot.organization_id == org_id,
                NetWorthSnapshot.user_id == None,  # noqa: E711 household rollup
            )
        )
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snapshot = snapshot_result.scalar_one_or_none()

    net_worth = float(snapshot.total_net_worth) if snapshot else 0.0
    snapshot_liquid = (
        float((snapshot.cash_and_checking or 0) + (snapshot.savings or 0))
        if snapshot
        else 0.0
    )

    # ── Live liquid asset balances from accounts ─────────────────────────────
    liquid_result = await db.execute(
        select(func.sum(Account.current_balance)).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_(_LIQUID_TYPES),
                Account.is_active.is_(True),  # noqa: E712
            )
        )
    )
    live_liquid = float(liquid_result.scalar() or 0)
    liquid_assets = live_liquid if live_liquid > 0 else snapshot_liquid

    # ── Total debt balances ───────────────────────────────────────────────────
    debt_result = await db.execute(
        select(func.sum(Account.current_balance)).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_(_DEBT_TYPES),
                Account.is_active.is_(True),  # noqa: E712
            )
        )
    )
    total_debt = float(debt_result.scalar() or 0)

    # ── Minimum monthly debt payments ────────────────────────────────────────
    debt_payment_result = await db.execute(
        select(func.sum(Account.minimum_payment)).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_(_DEBT_TYPES),
                Account.is_active.is_(True),  # noqa: E712
            )
        )
    )
    total_monthly_debt_payments = float(debt_payment_result.scalar() or 0)

    # ── Housing monthly costs (mortgage minimum payment) ─────────────────────
    housing_result = await db.execute(
        select(func.sum(Account.minimum_payment)).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_(_MORTGAGE_TYPES),
                Account.is_active.is_(True),  # noqa: E712
            )
        )
    )
    housing_monthly = float(housing_result.scalar() or 0)

    income_provided = monthly_income is not None and monthly_income > 0
    spending_provided = monthly_spending is not None and monthly_spending > 0

    # ── Compute ratios ────────────────────────────────────────────────────────

    # Savings rate: (income - spending) / income
    savings_rate: Optional[float] = None
    if income_provided and spending_provided:
        savings_rate = (monthly_income - monthly_spending) / monthly_income

    # DTI: total monthly debt payments / monthly income
    dti: Optional[float] = None
    if income_provided and total_monthly_debt_payments > 0:
        dti = total_monthly_debt_payments / monthly_income
    elif income_provided:
        dti = 0.0

    # Emergency fund: liquid / monthly spending
    emergency_months: Optional[float] = None
    if spending_provided and monthly_spending > 0:
        emergency_months = liquid_assets / monthly_spending

    # Housing ratio: housing monthly / income
    housing_ratio: Optional[float] = None
    if income_provided and housing_monthly > 0:
        housing_ratio = housing_monthly / monthly_income
    elif income_provided:
        housing_ratio = 0.0

    # ── Build metric objects ──────────────────────────────────────────────────
    metrics: List[RatioMetric] = []

    # Savings rate
    sr_grade = _grade_savings_rate(savings_rate)
    metrics.append(
        _make_metric(
            name="Savings Rate",
            value=savings_rate,
            formatted=(
                f"{savings_rate * 100:.1f}%" if savings_rate is not None else "N/A (income required)"
            ),
            grade=sr_grade,
            threshold_excellent="≥ 20%",
            threshold_good="≥ 10%",
            description="Percentage of gross income saved or invested each month.",
        )
    )

    # DTI
    dti_grade = _grade_dti(dti)
    metrics.append(
        _make_metric(
            name="Debt-to-Income (DTI)",
            value=dti,
            formatted=(
                f"{dti * 100:.1f}%" if dti is not None else "N/A (income required)"
            ),
            grade=dti_grade,
            threshold_excellent="≤ 15%",
            threshold_good="≤ 28%",
            description="Total monthly debt payments as a percentage of gross monthly income.",
        )
    )

    # Emergency fund
    ef_grade = _grade_emergency_fund(emergency_months)
    metrics.append(
        _make_metric(
            name="Emergency Fund",
            value=emergency_months,
            formatted=(
                f"{emergency_months:.1f} months"
                if emergency_months is not None
                else "N/A (spending required)"
            ),
            grade=ef_grade,
            threshold_excellent="≥ 6 months",
            threshold_good="≥ 3 months",
            description="How many months of expenses your liquid savings can cover.",
        )
    )

    # Housing ratio
    hr_grade = _grade_housing_ratio(housing_ratio)
    metrics.append(
        _make_metric(
            name="Housing Cost Ratio",
            value=housing_ratio,
            formatted=(
                f"{housing_ratio * 100:.1f}%"
                if housing_ratio is not None
                else "N/A (income required)"
            ),
            grade=hr_grade,
            threshold_excellent="≤ 25%",
            threshold_good="≤ 30%",
            description="Monthly mortgage/rent payment as a percentage of gross monthly income.",
        )
    )

    # ── Overall score ─────────────────────────────────────────────────────────
    scored = [
        _SCORE_FROM_GRADE[m.grade]
        for m in metrics
        if m.value is not None
    ]
    overall_score = sum(scored) / len(scored) if scored else 50.0
    overall_letter = _overall_grade(overall_score)

    # ── Tips ─────────────────────────────────────────────────────────────────
    tips: List[str] = []
    if not income_provided:
        tips.append("Provide monthly_income to unlock DTI, savings rate, and housing ratio grades.")
    if not spending_provided:
        tips.append("Provide monthly_spending to unlock emergency fund coverage calculation.")
    if savings_rate is not None and savings_rate < 0.10:
        tips.append("Aim to save at least 10–20% of gross income to build long-term wealth.")
    if dti is not None and dti > 0.28:
        tips.append("Your DTI is elevated — consider accelerating debt payoff starting with the highest-rate balances.")
    if emergency_months is not None and emergency_months < 3:
        tips.append("Build your emergency fund to at least 3 months of expenses before aggressively investing.")
    if housing_ratio is not None and housing_ratio > 0.30:
        tips.append("Housing costs exceed 30% of income — look for ways to reduce this through refinancing or additional income.")
    if not tips:
        tips.append("Great job — your financial ratios look healthy. Keep reviewing annually or after major life changes.")

    return FinancialRatiosResponse(
        metrics=metrics,
        overall_grade=overall_letter,
        overall_score=round(overall_score, 1),
        net_worth=net_worth,
        liquid_assets=liquid_assets,
        total_debt=total_debt,
        income_provided=income_provided,
        spending_provided=spending_provided,
        tips=tips,
    )
