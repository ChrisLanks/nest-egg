"""Savings goals API endpoints."""

import logging
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, verify_household_member
from app.models.savings_goal import SavingsGoal
from app.models.user import User
from app.schemas.savings_goal import (
    AutoSyncRequest,
    ReorderRequest,
    SavingsGoalCreate,
    SavingsGoalProgressResponse,
    SavingsGoalResponse,
    SavingsGoalUpdate,
)
from app.services.input_sanitization_service import input_sanitization_service
from app.services.savings_goal_service import savings_goal_service
from app.services.rate_limit_service import rate_limit_service
from app.utils.datetime_utils import utc_now


class LinkToRetirementRequest(BaseModel):
    scenario_id: UUID


class GoalTemplate(str, Enum):
    emergency_fund = "emergency_fund"
    vacation_fund = "vacation_fund"
    home_down_payment = "home_down_payment"
    debt_payoff_reserve = "debt_payoff_reserve"


class GoalFromTemplateRequest(BaseModel):
    template: GoalTemplate


class ContributionRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Contribution amount (must be positive)")


router = APIRouter()


@router.post("/", response_model=SavingsGoalResponse, status_code=201)
async def create_goal(
    goal_data: SavingsGoalCreate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new savings goal."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=3600, identifier=str(current_user.id)
    )
    # Sanitize user text input
    sanitized = goal_data.model_dump()
    if sanitized.get("name"):
        sanitized["name"] = input_sanitization_service.sanitize_html(sanitized["name"])
    if sanitized.get("description"):
        sanitized["description"] = input_sanitization_service.sanitize_html(
            sanitized["description"]
        )
    goal = await savings_goal_service.create_goal(
        db=db,
        user=current_user,
        **sanitized,
    )
    return goal


@router.get("/", response_model=List[SavingsGoalResponse])
async def list_goals(
    is_completed: Optional[bool] = None,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all savings goals for current user's organization."""
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
    goals = await savings_goal_service.get_goals(
        db=db,
        user=current_user,
        is_completed=is_completed,
        user_id=user_id,
    )
    return goals


# --- Collection-level routes must come BEFORE /{goal_id} to avoid path conflicts ---


@router.post("/from-template", response_model=SavingsGoalResponse, status_code=201)
async def create_goal_from_template(
    body: GoalFromTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a savings goal from a built-in template.

    Currently supported templates:
    - **emergency_fund**: calculates target from avg monthly expenses × 6,
      auto-links to the highest-balance checking/savings account.
    """
    template_methods = {
        GoalTemplate.emergency_fund: savings_goal_service.create_emergency_fund_goal,
        GoalTemplate.vacation_fund: savings_goal_service.create_vacation_fund_goal,
        GoalTemplate.home_down_payment: savings_goal_service.create_home_down_payment_goal,
        GoalTemplate.debt_payoff_reserve: savings_goal_service.create_debt_payoff_reserve_goal,
    }
    method = template_methods.get(body.template)
    if not method:
        raise HTTPException(status_code=400, detail=f"Unknown template: {body.template}")

    goal = await method(db=db, user=current_user)
    return goal


@router.post("/auto-sync", response_model=List[SavingsGoalResponse])
async def auto_sync_goals(
    request: AutoSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync all active auto-sync goals from their linked accounts.

    Allocation method controls how balance is split when multiple goals
    share the same account:
    - waterfall: priority order, each goal claims up to its target
    - proportional: balance split proportionally by target amounts
    """
    try:
        updated = await savings_goal_service.auto_sync_goals(
            db=db,
            user=current_user,
            method=request.method,
        )
    except Exception:
        logger.exception("auto-sync goals failed")
        raise HTTPException(status_code=500, detail="Failed to sync goals — check server logs")
    return updated


@router.put("/reorder", status_code=204)
async def reorder_goals(
    request: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder goals by updating their priority based on the provided order."""
    await savings_goal_service.reorder_goals(
        db=db,
        user=current_user,
        goal_ids=request.goal_ids,
    )


# --- Per-goal routes ---


@router.get("/{goal_id}", response_model=SavingsGoalResponse)
async def get_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific savings goal."""
    goal = await savings_goal_service.get_goal(
        db=db,
        goal_id=goal_id,
        user=current_user,
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    return goal


@router.patch("/{goal_id}", response_model=SavingsGoalResponse)
async def update_goal(
    goal_id: UUID,
    goal_data: SavingsGoalUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a savings goal."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=60, window_seconds=3600, identifier=str(current_user.id)
    )
    # Sanitize user text input
    sanitized = goal_data.model_dump(exclude_unset=True)
    if sanitized.get("name"):
        sanitized["name"] = input_sanitization_service.sanitize_html(sanitized["name"])
    if sanitized.get("description"):
        sanitized["description"] = input_sanitization_service.sanitize_html(
            sanitized["description"]
        )
    try:
        goal = await savings_goal_service.update_goal(
            db=db,
            goal_id=goal_id,
            user=current_user,
            **sanitized,
        )
    except Exception:
        logger.exception("update_goal failed for goal %s", goal_id)
        raise HTTPException(status_code=500, detail="Failed to update goal — check server logs")

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    return goal


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a savings goal."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=20, window_seconds=3600, identifier=str(current_user.id)
    )
    success = await savings_goal_service.delete_goal(
        db=db,
        goal_id=goal_id,
        user=current_user,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Savings goal not found")


@router.post("/{goal_id}/sync", response_model=SavingsGoalResponse)
async def sync_goal_from_account(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync goal's current amount from linked account balance."""
    goal = await savings_goal_service.sync_goal_from_account(
        db=db,
        goal_id=goal_id,
        user=current_user,
    )

    if not goal:
        raise HTTPException(
            status_code=404,
            detail="Savings goal not found or no account linked",
        )

    return goal


@router.post("/{goal_id}/fund", response_model=SavingsGoalResponse)
async def fund_goal(
    goal_id: UUID,
    request: AutoSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a goal as funded (money has been used for the goal).

    The goal moves to the completed section. Remaining active auto-sync
    goals are recalculated so the funded goal's account balance is
    redistributed to remaining goals.
    """
    goal = await savings_goal_service.fund_goal(
        db=db,
        goal_id=goal_id,
        user=current_user,
        method=request.method,
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    return goal


@router.get("/{goal_id}/progress", response_model=SavingsGoalProgressResponse)
async def get_goal_progress(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get progress metrics for a savings goal."""
    try:
        progress = await savings_goal_service.get_goal_progress(
            db=db,
            goal_id=goal_id,
            user=current_user,
        )
    except Exception:
        logger.exception("get_goal_progress failed for goal %s", goal_id)
        raise HTTPException(status_code=500, detail="Failed to compute goal progress")

    if not progress:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    return progress


@router.post("/{goal_id}/contributions")
async def record_contribution(
    goal_id: UUID,
    body: ContributionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record a member contribution to a shared savings goal.

    Updates the member_contributions JSON and increments current_amount.
    """
    # Use get_goal so that ownership/sharing rules are enforced consistently
    goal = await savings_goal_service.get_goal(db, goal_id, current_user)

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    if goal.is_completed:
        raise HTTPException(status_code=400, detail="Cannot contribute to a completed goal")

    # Update member_contributions JSON
    contributions = dict(goal.member_contributions or {})
    user_key = str(current_user.id)
    previous = Decimal(str(contributions.get(user_key, "0")))
    contributions[user_key] = str(previous + body.amount)
    goal.member_contributions = contributions

    # Increment current_amount
    goal.current_amount = (goal.current_amount or Decimal("0")) + body.amount
    goal.updated_at = utc_now()

    await db.commit()
    await db.refresh(goal)

    return {
        "goal_id": str(goal.id),
        "goal_name": goal.name,
        "contribution_amount": float(body.amount),
        "user_total_contributions": float(Decimal(contributions[user_key])),
        "current_amount": float(goal.current_amount),
        "target_amount": float(goal.target_amount),
        "member_contributions": {k: float(Decimal(v)) for k, v in contributions.items()},
    }


@router.post("/{goal_id}/add-to-retirement-plan")
async def add_goal_to_retirement_plan(
    goal_id: UUID,
    body: LinkToRetirementRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert a savings goal into a life event in a retirement scenario.

    Creates a one-time cost life event at the goal's target date
    with the goal's target amount.
    """
    from app.models.retirement import LifeEvent, LifeEventCategory, RetirementScenario
    from app.utils.rmd_calculator import calculate_age

    goal = await savings_goal_service.get_goal(db, goal_id, current_user)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    # Verify scenario ownership
    scenario_result = await db.execute(
        select(RetirementScenario).where(
            and_(
                RetirementScenario.id == body.scenario_id,
                RetirementScenario.organization_id == current_user.organization_id,
            )
        )
    )
    scenario = scenario_result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Retirement scenario not found")

    # Calculate age at target date
    if not current_user.birthdate:
        raise HTTPException(status_code=400, detail="User birthdate required")

    current_age = calculate_age(current_user.birthdate)
    if goal.target_date:
        # Use calculate_age to get exact age at target_date (accounts for leap years + birthday timing)
        target_age = calculate_age(current_user.birthdate, as_of_date=goal.target_date)
    else:
        target_age = current_age + 5  # Default: 5 years from now

    life_event = LifeEvent(
        scenario_id=body.scenario_id,
        name=f"Goal: {goal.name}",
        category=LifeEventCategory.CUSTOM,
        start_age=target_age,
        end_age=None,  # One-time event
        one_time_cost=goal.target_amount,
        annual_cost=None,
        income_change=None,
        use_medical_inflation=False,
        is_preset=False,
    )
    db.add(life_event)
    await db.commit()
    await db.refresh(life_event)

    return {
        "life_event_id": str(life_event.id),
        "scenario_id": str(body.scenario_id),
        "goal_name": goal.name,
        "target_age": target_age,
        "one_time_cost": float(goal.target_amount),
        "message": f"Savings goal '{goal.name}' added as life event at age {target_age}",
    }
