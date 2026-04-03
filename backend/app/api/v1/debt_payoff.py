"""Debt Payoff API endpoints."""

from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, verify_household_member
from app.services.rate_limit_service import rate_limit_service
from app.models.user import User
from app.services.payoff_strategy_service import PayoffStrategyService



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(dependencies=[Depends(_rate_limit)])


@router.get("/debts", response_model=Dict[str, Any])
async def list_debt_accounts(
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all debt accounts with calculated minimum payments.

    Returns debt accounts (credit cards, loans, student loans, mortgages)
    with positive balances and estimated/actual minimum payments.
    """
    # Verify household member if filtering by user
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    debts = await PayoffStrategyService.get_debt_accounts(db, current_user.organization_id, user_id)

    return [
        {
            "account_id": str(debt.account_id),
            "name": debt.name,
            "balance": float(debt.balance),
            "interest_rate": float(debt.interest_rate),
            "minimum_payment": float(debt.minimum_payment),
            "account_type": debt.account_type,
        }
        for debt in debts
    ]


@router.get("/compare", response_model=Dict[str, Any])
async def compare_payoff_strategies(
    extra_payment: Decimal = Query(..., description="Extra monthly payment amount"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    account_ids: Optional[str] = Query(None, description="Comma-separated account IDs to include"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare debt payoff strategies (snowball, avalanche, current pace).

    Returns side-by-side comparison showing:
    - Snowball: Pay off smallest balance first (psychological wins)
    - Avalanche: Pay off highest interest first (maximum savings)
    - Current Pace: Minimum payments only (baseline)

    Each strategy includes:
    - Total months to debt-free
    - Total interest paid
    - Total amount paid
    - Debt-free date
    - Per-debt payoff timeline
    - Interest/time savings vs current pace
    """
    # Verify household member if filtering by user
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    # Parse account IDs if provided
    account_id_list = None
    if account_ids:
        try:
            account_id_list = [UUID(id.strip()) for id in account_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid account_ids format")

    comparison = await PayoffStrategyService.compare_strategies(
        db, current_user.organization_id, extra_payment, user_id, account_id_list
    )

    return comparison


@router.get("/summary", response_model=Dict[str, Any])
async def get_debt_summary(
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get high-level debt summary.

    Returns:
    - Total debt balance
    - Total monthly minimum payments
    - Average interest rate (weighted by balance)
    - Number of debt accounts
    """
    # Verify household member if filtering by user
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    debts = await PayoffStrategyService.get_debt_accounts(db, current_user.organization_id, user_id)

    if not debts:
        return {
            "total_debt": 0,
            "total_minimum_payment": 0,
            "average_interest_rate": 0,
            "debt_count": 0,
        }

    total_debt = sum(debt.balance for debt in debts)
    total_minimum = sum(debt.minimum_payment for debt in debts)

    # Calculate weighted average interest rate
    weighted_rate_sum = sum(debt.balance * debt.interest_rate for debt in debts)
    avg_rate = weighted_rate_sum / total_debt if total_debt > 0 else Decimal(0)

    return {
        "total_debt": float(total_debt),
        "total_minimum_payment": float(total_minimum),
        "average_interest_rate": float(avg_rate),
        "debt_count": len(debts),
    }


@router.get("/debts/{account_id}/amortization", response_model=Dict[str, Any])
async def get_loan_amortization(
    account_id: UUID,
    extra_payment: Decimal = Query(Decimal("0"), ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate amortization schedule for a loan account (up to 24 months shown).
    Returns monthly payment breakdown: principal, interest, remaining balance.
    """
    from datetime import date as date_type
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import select
    from app.models.account import Account

    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if not account.interest_rate or account.interest_rate <= 0:
        raise HTTPException(status_code=400, detail="Account has no interest rate set")
    if not account.minimum_payment or account.minimum_payment <= 0:
        raise HTTPException(status_code=400, detail="Account has no minimum payment set")

    balance = abs(float(account.current_balance or 0))
    annual_rate = float(account.interest_rate) / 100
    monthly_rate = annual_rate / 12
    monthly_payment = float(account.minimum_payment) + float(extra_payment)

    if monthly_rate > 0 and monthly_payment <= balance * monthly_rate:
        raise HTTPException(status_code=400, detail="Monthly payment too small to cover interest")

    schedule = []
    total_interest = 0.0
    total_paid = 0.0
    current_balance = balance
    current_date = date_type.today()
    MAX_MONTHS = 360

    for month in range(1, MAX_MONTHS + 1):
        if current_balance <= 0.005:
            break
        interest = current_balance * monthly_rate if monthly_rate > 0 else 0.0
        payment = min(monthly_payment, current_balance + interest)
        principal = payment - interest
        current_balance = max(0.0, current_balance - principal)
        total_interest += interest
        total_paid += payment
        payment_date = current_date + relativedelta(months=month)

        schedule.append({
            "month": month,
            "date": payment_date.isoformat(),
            "payment": round(payment, 2),
            "principal": round(principal, 2),
            "interest": round(interest, 2),
            "balance": round(current_balance, 2),
        })

    return {
        "schedule": schedule[:24],  # Return first 24 months in response
        "total_months": len(schedule),
        "total_interest": round(total_interest, 2),
        "total_paid": round(total_paid, 2),
        "monthly_payment": round(monthly_payment, 2),
        "payoff_date": schedule[-1]["date"] if schedule else None,
    }