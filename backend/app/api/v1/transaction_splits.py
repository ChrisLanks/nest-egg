"""Transaction splits API endpoints."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.transaction_split import (
    MemberBalanceResponse,
    SettleRequest,
    SettleResponse,
    TransactionSplitUpdate,
    TransactionSplitResponse,
    CreateSplitsRequest,
)
from app.services.transaction_split_service import transaction_split_service
from app.services.rate_limit_service import rate_limit_service

router = APIRouter()


@router.post("/", response_model=List[TransactionSplitResponse], status_code=201)
async def create_transaction_splits(
    split_request: CreateSplitsRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create multiple splits for a transaction.

    The sum of split amounts must equal the transaction amount.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=60, window_seconds=3600, identifier=str(current_user.id)
    )
    try:
        splits = await transaction_split_service.create_splits(
            db=db,
            transaction_id=split_request.transaction_id,
            splits_data=[split.model_dump() for split in split_request.splits],
            user=current_user,
        )
        return splits
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid split request")


@router.get("/transaction/{transaction_id}", response_model=List[TransactionSplitResponse])
async def get_transaction_splits(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all splits for a transaction."""
    splits = await transaction_split_service.get_transaction_splits(
        db=db,
        transaction_id=transaction_id,
        user=current_user,
    )
    return splits


@router.patch("/{split_id}", response_model=TransactionSplitResponse)
async def update_split(
    split_id: UUID,
    split_data: TransactionSplitUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a single split."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=60, window_seconds=3600, identifier=str(current_user.id)
    )
    try:
        split = await transaction_split_service.update_split(
            db=db,
            split_id=split_id,
            user=current_user,
            **split_data.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        # Use generic message — split service errors may contain stored amounts
        raise HTTPException(status_code=400, detail="Invalid split update")

    if not split:
        raise HTTPException(status_code=404, detail="Split not found")

    return split


@router.delete("/transaction/{transaction_id}", status_code=204)
async def delete_transaction_splits(
    transaction_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all splits for a transaction and mark it as not split."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=3600, identifier=str(current_user.id)
    )
    success = await transaction_split_service.delete_splits(
        db=db,
        transaction_id=transaction_id,
        user=current_user,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")


@router.get("/member-balances", response_model=List[MemberBalanceResponse])
async def get_member_balances(
    since: Optional[date] = Query(None, description="Only include splits from this date onward."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return per-member expense totals derived from assigned transaction splits.

    Useful for household settlement: shows who has paid how much and who owes whom.
    """
    balances = await transaction_split_service.get_member_balances(
        db=db,
        organization_id=current_user.organization_id,
        since_date=since,
    )
    return balances


@router.post("/settle", response_model=SettleResponse)
async def settle_member_balance(
    settle_request: SettleRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all unsettled splits assigned to a household member as settled.

    Fires a SETTLEMENT_REMINDER notification to the member when settled by
    another household member (e.g. admin confirming payment received).
    """
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=60, window_seconds=3600, identifier=str(current_user.id)
    )
    from datetime import date as date_type

    since_date = None
    if settle_request.since:
        try:
            since_date = date_type.fromisoformat(settle_request.since)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid since date format; use YYYY-MM-DD")

    count = await transaction_split_service.settle_member(
        db=db,
        member_id=settle_request.member_id,
        organization_id=current_user.organization_id,
        since_date=since_date,
        settled_by=current_user,
    )
    return SettleResponse(settled_count=count)
