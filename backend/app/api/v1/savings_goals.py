"""Savings goals API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.savings_goal import (
    SavingsGoalCreate,
    SavingsGoalUpdate,
    SavingsGoalResponse,
    SavingsGoalProgressResponse,
)
from app.services.savings_goal_service import savings_goal_service

router = APIRouter()


@router.post("/", response_model=SavingsGoalResponse, status_code=201)
async def create_goal(
    goal_data: SavingsGoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new savings goal."""
    goal = await savings_goal_service.create_goal(
        db=db,
        user=current_user,
        **goal_data.model_dump(),
    )
    return goal


@router.get("/", response_model=List[SavingsGoalResponse])
async def list_goals(
    is_completed: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all savings goals for current user's organization."""
    goals = await savings_goal_service.get_goals(
        db=db,
        user=current_user,
        is_completed=is_completed,
    )
    return goals


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a savings goal."""
    goal = await savings_goal_service.update_goal(
        db=db,
        goal_id=goal_id,
        user=current_user,
        **goal_data.model_dump(exclude_unset=True),
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    return goal


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a savings goal."""
    success = await savings_goal_service.delete_goal(
        db=db,
        goal_id=goal_id,
        user=current_user,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Savings goal not found")


@router.post("/{goal_id}/sync")
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


@router.get("/{goal_id}/progress", response_model=SavingsGoalProgressResponse)
async def get_goal_progress(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get progress metrics for a savings goal."""
    progress = await savings_goal_service.get_goal_progress(
        db=db,
        goal_id=goal_id,
        user=current_user,
    )

    if not progress:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    return progress
