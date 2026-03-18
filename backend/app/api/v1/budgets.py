"""Budget API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, verify_household_member
from app.models.user import User
from app.schemas.budget import (
    BudgetCreate,
    BudgetResponse,
    BudgetSpendingResponse,
    BudgetUpdate,
)
from app.services.budget_service import budget_service
from app.services.budget_suggestion_service import budget_suggestion_service
from app.services.input_sanitization_service import input_sanitization_service

router = APIRouter()


@router.post("/", response_model=BudgetResponse, status_code=201)
async def create_budget(
    budget_data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new budget."""
    # Sanitize user text input
    sanitized = budget_data.model_dump()
    if sanitized.get("name"):
        sanitized["name"] = input_sanitization_service.sanitize_html(sanitized["name"])
    budget = await budget_service.create_budget(
        db=db,
        user=current_user,
        **sanitized,
    )
    return budget


@router.get("/", response_model=List[BudgetResponse])
async def list_budgets(
    is_active: Optional[bool] = None,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all budgets for current user's organization."""
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
    budgets = await budget_service.get_budgets(
        db=db,
        user=current_user,
        is_active=is_active,
        user_id=user_id,
    )
    return budgets


# CSV Export must be defined before /{budget_id} to avoid route shadowing
@router.get("/export/csv")
async def export_budgets_csv(
    request: Request,
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = all household budgets"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export budgets as a CSV file.

    Returns budgets with their configuration and status, suitable for
    spreadsheet applications or archival purposes.
    Accepts optional user_id to filter to a specific member's budgets.
    """
    import csv
    from io import StringIO

    from fastapi.responses import StreamingResponse

    from app.services.rate_limit_service import rate_limit_service

    # Rate limit: 10 exports per hour per user
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=10,
        window_seconds=3600,
        identifier=str(current_user.id),
    )

    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
    # Reuse the service which already handles user_id filtering
    budgets = await budget_service.get_budgets(db=db, user=current_user, user_id=user_id)

    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "Budget Name",
            "Amount",
            "Period",
            "Start Date",
            "End Date",
            "Alert Threshold",
            "Rollover Unused",
            "Is Active",
            "Is Shared",
            "Created At",
            "Budget ID",
        ]
    )

    # Write rows
    for budget in budgets:
        writer.writerow(
            [
                budget.name,
                float(budget.amount),
                budget.period.value if budget.period else "",
                budget.start_date.isoformat() if budget.start_date else "",
                budget.end_date.isoformat() if budget.end_date else "",
                float(budget.alert_threshold) if budget.alert_threshold is not None else "",
                "Yes" if budget.rollover_unused else "No",
                "Yes" if budget.is_active else "No",
                "Yes" if budget.is_shared else "No",
                budget.created_at.isoformat() if budget.created_at else "",
                str(budget.id),
            ]
        )

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="budgets.csv"'},
    )


@router.get("/suggestions")
async def get_budget_suggestions(
    months: int = Query(6, ge=1, le=24, description="Months of history to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get smart budget suggestions based on spending history.

    Analyzes transaction history to find top spending categories
    and suggests appropriate budget amounts and periods.
    """
    return await budget_suggestion_service.get_suggestions(
        db=db,
        user=current_user,
        months=months,
    )


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
    # Sanitize user text input
    sanitized = budget_data.model_dump(exclude_unset=True)
    if sanitized.get("name"):
        sanitized["name"] = input_sanitization_service.sanitize_html(sanitized["name"])
    budget = await budget_service.update_budget(
        db=db,
        budget_id=budget_id,
        user=current_user,
        **sanitized,
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
