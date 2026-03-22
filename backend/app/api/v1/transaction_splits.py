"""Transaction splits API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.transaction_split import (
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
        raise HTTPException(status_code=400, detail=str(e))

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
