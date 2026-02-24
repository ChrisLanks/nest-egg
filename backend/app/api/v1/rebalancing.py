"""Portfolio rebalancing API endpoints."""

import uuid
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.holding import Holding
from app.models.target_allocation import TargetAllocation
from app.models.user import User
from app.schemas.target_allocation import (
    AllocationSlice,
    RebalancingAnalysis,
    TargetAllocationCreate,
    TargetAllocationResponse,
    TargetAllocationUpdate,
)
from app.services.rebalancing_service import PRESET_PORTFOLIOS, RebalancingService

router = APIRouter()


@router.get("/presets")
async def get_presets(
    current_user: User = Depends(get_current_user),
):
    """Return preset portfolio allocations."""
    return RebalancingService.get_presets()


@router.get("/target-allocations", response_model=List[TargetAllocationResponse])
async def list_target_allocations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's target allocations filtered by organization."""
    result = await db.execute(
        select(TargetAllocation)
        .where(
            TargetAllocation.organization_id == current_user.organization_id,
            TargetAllocation.user_id == current_user.id,
        )
        .order_by(TargetAllocation.updated_at.desc())
    )
    allocations = result.scalars().all()
    return allocations


@router.post("/target-allocations", response_model=TargetAllocationResponse, status_code=201)
async def create_target_allocation(
    payload: TargetAllocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new target allocation.

    If the new allocation would be active (default), deactivate any existing
    active allocation for this user first.
    """
    # Deactivate existing active allocations for this user
    await RebalancingService.deactivate_other_allocations(
        db, current_user.organization_id, current_user.id
    )

    allocation = TargetAllocation(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        name=payload.name,
        allocations=[s.model_dump(mode="json") for s in payload.allocations],
        drift_threshold=payload.drift_threshold,
        is_active=True,
    )

    db.add(allocation)
    await db.commit()
    await db.refresh(allocation)
    return allocation


@router.post(
    "/target-allocations/from-preset",
    response_model=TargetAllocationResponse,
    status_code=201,
)
async def create_from_preset(
    preset_key: str = Query(..., description="Key of the preset portfolio"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a target allocation from a preset portfolio.

    Deactivates any existing active allocation for this user first.
    """
    preset = PRESET_PORTFOLIOS.get(preset_key)
    if not preset:
        valid_keys = ", ".join(PRESET_PORTFOLIOS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown preset key. Valid keys: {valid_keys}",
        )

    # Deactivate existing active allocations
    await RebalancingService.deactivate_other_allocations(
        db, current_user.organization_id, current_user.id
    )

    allocation = TargetAllocation(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        name=preset["name"],
        allocations=preset["allocations"],
        drift_threshold=Decimal("5.0"),
        is_active=True,
    )

    db.add(allocation)
    await db.commit()
    await db.refresh(allocation)
    return allocation


@router.patch("/target-allocations/{allocation_id}", response_model=TargetAllocationResponse)
async def update_target_allocation(
    allocation_id: UUID,
    payload: TargetAllocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a target allocation. Verify ownership (same org).

    If setting is_active=True, deactivate other active allocations first.
    """
    result = await db.execute(
        select(TargetAllocation).where(TargetAllocation.id == allocation_id)
    )
    allocation = result.scalar_one_or_none()

    if not allocation:
        raise HTTPException(status_code=404, detail="Target allocation not found")

    if (
        allocation.organization_id != current_user.organization_id
        or allocation.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    # If setting is_active=True, deactivate others first
    if payload.is_active is True:
        await RebalancingService.deactivate_other_allocations(
            db, current_user.organization_id, current_user.id, exclude_id=allocation_id
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Serialize allocations to JSON-compatible format
    if "allocations" in update_data and update_data["allocations"] is not None:
        update_data["allocations"] = [
            s.model_dump(mode="json") for s in payload.allocations
        ]

    for key, value in update_data.items():
        setattr(allocation, key, value)

    await db.commit()
    await db.refresh(allocation)
    return allocation


@router.delete("/target-allocations/{allocation_id}", status_code=204)
async def delete_target_allocation(
    allocation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a target allocation. Verify ownership (same org)."""
    result = await db.execute(
        select(TargetAllocation).where(TargetAllocation.id == allocation_id)
    )
    allocation = result.scalar_one_or_none()

    if not allocation:
        raise HTTPException(status_code=404, detail="Target allocation not found")

    if (
        allocation.organization_id != current_user.organization_id
        or allocation.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(allocation)
    await db.commit()


@router.get("/analysis", response_model=RebalancingAnalysis)
async def get_rebalancing_analysis(
    user_id: Optional[UUID] = Query(None, description="Filter holdings by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch active allocation and current portfolio data, then compute drift analysis.

    Queries holdings grouped by asset_class and sums current_total_value.
    Returns drift items, trade recommendations, and rebalancing flag.
    """
    # Get active allocation
    active = await RebalancingService.get_active_allocation(
        db, current_user.organization_id, current_user.id
    )
    if not active:
        raise HTTPException(
            status_code=404,
            detail="No active target allocation found. Create one first.",
        )

    # Build holdings query: group by asset_class, sum current_total_value
    holdings_conditions = [
        Holding.organization_id == current_user.organization_id,
    ]
    if user_id is not None:
        # Filter holdings by accounts owned by that user
        from app.models.account import Account

        holdings_conditions.append(
            Holding.account_id.in_(
                select(Account.id).where(
                    Account.user_id == user_id,
                    Account.organization_id == current_user.organization_id,
                )
            )
        )

    result = await db.execute(
        select(
            Holding.asset_class,
            func.sum(Holding.current_total_value).label("total_value"),
        )
        .where(and_(*holdings_conditions))
        .group_by(Holding.asset_class)
    )
    rows = result.all()

    current_by_class = {}
    portfolio_total = Decimal("0")
    for row in rows:
        asset_class = row.asset_class or "other"
        value = Decimal(str(row.total_value)) if row.total_value else Decimal("0")
        current_by_class[asset_class] = current_by_class.get(asset_class, Decimal("0")) + value
        portfolio_total += value

    # Parse stored allocations into AllocationSlice objects
    target_slices = [AllocationSlice(**s) for s in active.allocations]

    drift_items, trade_recs, needs_rebalancing, max_drift = RebalancingService.calculate_drift(
        target_slices, current_by_class, portfolio_total, active.drift_threshold
    )

    return RebalancingAnalysis(
        target_allocation_id=active.id,
        target_allocation_name=active.name,
        portfolio_total=portfolio_total,
        drift_items=drift_items,
        needs_rebalancing=needs_rebalancing,
        max_drift_percent=max_drift,
        trade_recommendations=trade_recs,
    )
