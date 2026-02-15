"""Budget API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetSpendingResponse,
)
from app.services.budget_service import budget_service

router = APIRouter()


@router.post("/", response_model=BudgetResponse, status_code=201)
async def create_budget(
    budget_data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new budget."""
    budget = await budget_service.create_budget(
        db=db,
        user=current_user,
        **budget_data.model_dump(),
    )
    return budget


@router.get("/", response_model=List[BudgetResponse])
async def list_budgets(
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all budgets for current user's organization."""
    budgets = await budget_service.get_budgets(
        db=db,
        user=current_user,
        is_active=is_active,
    )
    return budgets


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific budget."""
    budget = await budget_service.get_budget(
        db=db,
        budget_id=budget_id,
        user=current_user,
    )

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    return budget


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: UUID,
    budget_data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a budget."""
    budget = await budget_service.update_budget(
        db=db,
        budget_id=budget_id,
        user=current_user,
        **budget_data.model_dump(exclude_unset=True),
    )

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    return budget


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a budget."""
    success = await budget_service.delete_budget(
        db=db,
        budget_id=budget_id,
        user=current_user,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")


@router.get("/{budget_id}/spending", response_model=BudgetSpendingResponse)
async def get_budget_spending(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get spending for a budget in the current period."""
    spending = await budget_service.get_budget_spending(
        db=db,
        budget_id=budget_id,
        user=current_user,
    )

    if not spending:
        raise HTTPException(status_code=404, detail="Budget not found")

    return spending


@router.post("/check-alerts")
async def check_budget_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check all budgets and create alerts for those exceeding threshold."""
    alerts = await budget_service.check_budget_alerts(db=db, user=current_user)
    return {"alerts_created": len(alerts), "budgets_alerted": alerts}
