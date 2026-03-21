"""Financial Health Score service.

Calculates a composite 0-100 score from four equally-weighted components:
savings rate, emergency fund coverage, debt-to-income ratio, and
retirement progress.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import HEALTH
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.utils.account_type_groups import (
    ALL_RETIREMENT_TYPES,
    CASH_ACCOUNT_TYPES,
    DEBT_ACCOUNT_TYPES,
)
from app.utils.datetime_utils import utc_now

# ---------------------------------------------------------------------------
# Grade mapping (from centralized constants)
# ---------------------------------------------------------------------------


def _grade(score: float) -> str:
    if score >= HEALTH.GRADE_A:
        return "A"
    if score >= HEALTH.GRADE_B:
        return "B"
    if score >= HEALTH.GRADE_C:
        return "C"
    if score >= HEALTH.GRADE_D:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Fidelity age-based retirement benchmarks (from centralized constants)
# ---------------------------------------------------------------------------

_RETIREMENT_BENCHMARKS = [(age, Decimal(mult)) for age, mult in HEALTH.RETIREMENT_BENCHMARKS]


def _retirement_target_multiple(age: int) -> Decimal:
    """Return the Fidelity benchmark multiple for a given age via linear interpolation."""
    if age <= HEALTH.RETIREMENT_BENCHMARK_MIN_AGE:
        return Decimal(HEALTH.RETIREMENT_BENCHMARK_MIN_MULT)
    if age >= HEALTH.RETIREMENT_BENCHMARK_MAX_AGE:
        return Decimal(HEALTH.RETIREMENT_BENCHMARK_MAX_MULT)
    for i in range(len(_RETIREMENT_BENCHMARKS) - 1):
        lo_age, lo_mult = _RETIREMENT_BENCHMARKS[i]
        hi_age, hi_mult = _RETIREMENT_BENCHMARKS[i + 1]
        if lo_age <= age <= hi_age:
            frac = Decimal(age - lo_age) / Decimal(hi_age - lo_age)
            return lo_mult + frac * (hi_mult - lo_mult)
    return Decimal(8)


# ---------------------------------------------------------------------------
# Component score helpers
# ---------------------------------------------------------------------------


def _savings_rate_score(monthly_savings: Decimal, monthly_income: Decimal) -> Dict[str, Any]:
    """Score the savings-rate component (0-100)."""
    if monthly_income <= 0:
        rate = Decimal(0)
        score = 0.0
    else:
        rate = monthly_savings / monthly_income
        pct = float(rate * 100)
        if pct >= HEALTH.SAVINGS_RATE_EXCELLENT:
            score = 100.0
        elif pct >= HEALTH.SAVINGS_RATE_GOOD:
            score = (
                50
                + (pct - HEALTH.SAVINGS_RATE_GOOD)
                / (HEALTH.SAVINGS_RATE_EXCELLENT - HEALTH.SAVINGS_RATE_GOOD)
                * 50
            )
        elif pct >= 0:
            score = pct / HEALTH.SAVINGS_RATE_GOOD * 50
        else:
            score = 0.0

    return {
        "score": round(score, 1),
        "value": round(float(rate * 100), 1),
        "label": "Savings Rate",
        "detail": f"{round(float(rate * 100), 1)}% of income saved",
    }


def _emergency_fund_score(liquid_savings: Decimal, monthly_expenses: Decimal) -> Dict[str, Any]:
    """Score the emergency-fund component (0-100)."""
    if monthly_expenses <= 0:
        months = float(6) if liquid_savings > 0 else 0.0
    else:
        months = float(liquid_savings / monthly_expenses)

    if months >= HEALTH.EMERGENCY_FUND_EXCELLENT:
        score = 100.0
    elif months >= HEALTH.EMERGENCY_FUND_GOOD:
        score = (
            50
            + (months - HEALTH.EMERGENCY_FUND_GOOD)
            / (HEALTH.EMERGENCY_FUND_EXCELLENT - HEALTH.EMERGENCY_FUND_GOOD)
            * 50
        )
    elif months >= 0:
        score = months / HEALTH.EMERGENCY_FUND_GOOD * 50
    else:
        score = 0.0

    return {
        "score": round(score, 1),
        "value": round(months, 1),
        "label": "Emergency Fund",
        "detail": f"{round(months, 1)} months of expenses covered",
    }


def _debt_to_income_score(
    monthly_debt_payments: Decimal,
    monthly_income: Decimal,
) -> Dict[str, Any]:
    """Score the debt-to-income component (0-100, inverse)."""
    if monthly_income <= 0:
        ratio = float(100) if monthly_debt_payments > 0 else 0.0
    else:
        ratio = float(monthly_debt_payments / monthly_income * 100)

    if ratio <= HEALTH.DTI_EXCELLENT:
        score = 100.0
    elif ratio <= HEALTH.DTI_FAIR:
        score = 50 + (HEALTH.DTI_FAIR - ratio) / (HEALTH.DTI_FAIR - HEALTH.DTI_EXCELLENT) * 50
    elif ratio <= HEALTH.DTI_UPPER_BOUND:
        score = (HEALTH.DTI_UPPER_BOUND - ratio) / (HEALTH.DTI_UPPER_BOUND - HEALTH.DTI_FAIR) * 50
    else:
        score = 0.0

    return {
        "score": round(max(score, 0.0), 1),
        "value": round(ratio, 1),
        "label": "Debt-to-Income",
        "detail": f"{round(ratio, 1)}% of income goes to debt",
    }


def _retirement_progress_score(
    retirement_balance: Decimal,
    annual_income: Decimal,
    age: Optional[int],
) -> Dict[str, Any]:
    """Score retirement progress based on Fidelity age benchmarks."""
    if age is None or annual_income <= 0:
        return {
            "score": 0.0,
            "value": 0.0,
            "label": "Retirement Progress",
            "detail": "Add birthdate and income data to calculate",
        }

    target_multiple = _retirement_target_multiple(age)
    target = annual_income * target_multiple
    if target <= 0:
        progress = 100.0 if retirement_balance > 0 else 0.0
    else:
        progress = float(retirement_balance / target * 100)

    if progress >= 100:
        score = 100.0
    elif progress >= HEALTH.RETIREMENT_SCORE_BAND_HIGH:
        score = HEALTH.RETIREMENT_SCORE_BAND_HIGH
    elif progress >= 50:
        score = 50.0
    elif progress >= HEALTH.RETIREMENT_SCORE_BAND_LOW:
        score = HEALTH.RETIREMENT_SCORE_BAND_LOW
    else:
        score = 0.0

    return {
        "score": score,
        "value": round(progress, 1),
        "label": "Retirement Progress",
        "detail": f"{round(progress, 1)}% of age-based target",
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def _build_recommendations(components: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return 1-3 actionable recommendations targeting the weakest areas."""
    ranked = sorted(components.items(), key=lambda kv: kv[1]["score"])
    recs: List[str] = []

    for key, comp in ranked:
        if len(recs) >= 3:
            break
        if comp["score"] >= 80:
            continue
        if key == "savings_rate":
            if comp["score"] < 50:
                recs.append(
                    "Aim to save at least 10% of your income each month. "
                    "Start by automating a small transfer to savings on payday."
                )
            else:
                recs.append(
                    "You're saving, but try to reach the 20% benchmark. "
                    "Look for one expense category to cut back on."
                )
        elif key == "emergency_fund":
            if comp["score"] < 50:
                recs.append(
                    "Build an emergency fund covering at least 3 months of expenses "
                    "in a high-yield savings account."
                )
            else:
                recs.append(
                    "Your emergency fund is growing. Keep going until you "
                    "reach 6 months of expenses."
                )
        elif key == "debt_to_income":
            if comp["score"] < 50:
                recs.append(
                    "Your debt payments are high relative to income. "
                    "Focus on paying down high-interest debt first."
                )
            else:
                recs.append(
                    "Continue reducing debt. Consider refinancing "
                    "high-interest loans for a lower rate."
                )
        elif key == "retirement_progress":
            if comp["score"] < 50:
                recs.append(
                    "Increase retirement contributions, especially if your "
                    "employer offers a 401(k) match you're not fully using."
                )
            else:
                recs.append(
                    "You're making progress on retirement. "
                    "Review your asset allocation to stay on track."
                )

    if not recs:
        recs.append("Great job! Keep maintaining your healthy financial habits.")

    return recs


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class FinancialHealthService:
    """Calculate a composite Financial Health Score (0-100)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate(
        self,
        organization_id: str,
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate the full financial health score.

        Parameters
        ----------
        organization_id : str
            Organization (household) to score.
        user_id : UUID | None
            Optional user to scope the query (for age / birthdate lookup).
        account_ids : list[UUID] | None
            Optional pre-filtered account ids (from the household dedup layer).
        """
        # -- 1. Fetch active accounts -----------------------------------------
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
        ]
        if account_ids is not None:
            conditions.append(Account.id.in_(account_ids))

        result = await self.db.execute(select(Account).where(and_(*conditions)))
        accounts: list[Account] = list(result.scalars().all())

        # -- 2. Aggregate account balances by category -------------------------
        liquid_savings = Decimal(0)
        retirement_balance = Decimal(0)
        total_debt_balance = Decimal(0)
        monthly_debt_payments = Decimal(0)

        for acct in accounts:
            balance = abs(acct.current_balance or Decimal(0))

            # Liquid savings: checking, savings, money market
            if acct.account_type in CASH_ACCOUNT_TYPES:
                liquid_savings += acct.current_balance or Decimal(0)

            # Retirement accounts
            if acct.account_type in ALL_RETIREMENT_TYPES:
                retirement_balance += acct.current_balance or Decimal(0)

            # Debt accounts
            if acct.account_type in DEBT_ACCOUNT_TYPES:
                total_debt_balance += balance
                if acct.minimum_payment:
                    monthly_debt_payments += acct.minimum_payment

        # -- 3. Get 3-month average income & expenses --------------------------
        now = utc_now()
        three_months_ago = date(now.year, now.month, 1) - timedelta(days=90)
        end = date(now.year, now.month, 1) - timedelta(days=1)  # end of last month

        txn_conditions = [
            Transaction.organization_id == organization_id,
            Transaction.date >= three_months_ago,
            Transaction.date <= end,
        ]
        if account_ids is not None:
            txn_conditions.append(Transaction.account_id.in_(account_ids))

        txn_result = await self.db.execute(
            select(
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                    "income"
                ),
                func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label(
                    "expenses"
                ),
            ).where(and_(*txn_conditions))
        )
        row = txn_result.one()
        total_income = row.income if row.income else Decimal(0)
        total_expenses = abs(row.expenses) if row.expenses else Decimal(0)

        monthly_income = total_income / 3
        monthly_expenses = total_expenses / 3
        monthly_savings = monthly_income - monthly_expenses
        annual_income = monthly_income * 12

        # -- 4. Determine user age (for retirement benchmark) ------------------
        age: Optional[int] = None
        if user_id:
            user_result = await self.db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user and user.birthdate:
                today = date.today()
                bd = user.birthdate
                age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

        # -- 5. Compute component scores ---------------------------------------
        components = {
            "savings_rate": _savings_rate_score(monthly_savings, monthly_income),
            "emergency_fund": _emergency_fund_score(liquid_savings, monthly_expenses),
            "debt_to_income": _debt_to_income_score(monthly_debt_payments, monthly_income),
            "retirement_progress": _retirement_progress_score(
                retirement_balance, annual_income, age
            ),
        }

        # -- 6. Weighted overall score -----------------------------------------
        overall = (
            components["savings_rate"]["score"] * 0.25
            + components["emergency_fund"]["score"] * 0.25
            + components["debt_to_income"]["score"] * 0.25
            + components["retirement_progress"]["score"] * 0.25
        )
        overall = round(overall, 1)

        return {
            "overall_score": overall,
            "grade": _grade(overall),
            "components": components,
            "recommendations": _build_recommendations(components),
        }
