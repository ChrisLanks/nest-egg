"""Debt Payoff API endpoints."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, verify_household_member
from app.models.user import User
from app.services.payoff_strategy_service import PayoffStrategyService

router = APIRouter()


@router.get("/debts")
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

    debts = await PayoffStrategyService.get_debt_accounts(
        db,
        current_user.organization_id,
        user_id
    )

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


@router.get("/compare")
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
            account_id_list = [UUID(id.strip()) for id in account_ids.split(',')]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid account_ids format")

    comparison = await PayoffStrategyService.compare_strategies(
        db,
        current_user.organization_id,
        extra_payment,
        user_id,
        account_id_list
    )

    return comparison


@router.get("/summary")
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

    debts = await PayoffStrategyService.get_debt_accounts(
        db,
        current_user.organization_id,
        user_id
    )

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
    weighted_rate_sum = sum(
        debt.balance * debt.interest_rate for debt in debts
    )
    avg_rate = weighted_rate_sum / total_debt if total_debt > 0 else Decimal(0)

    return {
        "total_debt": float(total_debt),
        "total_minimum_payment": float(total_minimum),
        "average_interest_rate": float(avg_rate),
        "debt_count": len(debts),
    }
