"""Transaction merges API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.transaction_merge import (
    TransactionMergeRequest,
    TransactionMergeResponse,
    DuplicateDetectionRequest,
)
from app.services.transaction_merge_service import transaction_merge_service

router = APIRouter()


@router.post("/find-duplicates")
async def find_potential_duplicates(
    request: DuplicateDetectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Find potential duplicate transactions for a given transaction."""
    duplicates = await transaction_merge_service.find_potential_duplicates(
        db=db,
        transaction_id=request.transaction_id,
        user=current_user,
        date_window_days=request.date_window_days,
        amount_tolerance=request.amount_tolerance,
    )

    return {
        "transaction_id": request.transaction_id,
        "potential_duplicates": duplicates,
        "count": len(duplicates),
    }


@router.post("/", response_model=TransactionMergeResponse, status_code=201)
async def merge_transactions(
    merge_request: TransactionMergeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Merge duplicate transactions into a primary transaction.

    The duplicate transactions will be deleted and a merge record created.
    """
    try:
        merge_record = await transaction_merge_service.merge_transactions(
            db=db,
            primary_transaction_id=merge_request.primary_transaction_id,
            duplicate_transaction_ids=merge_request.duplicate_transaction_ids,
            user=current_user,
            merge_reason=merge_request.merge_reason,
            is_auto_merged=False,
        )
        return merge_record
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid merge request")


@router.get("/transaction/{transaction_id}/history", response_model=List[TransactionMergeResponse])
async def get_merge_history(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get merge history for a transaction."""
    history = await transaction_merge_service.get_merge_history(
        db=db,
        transaction_id=transaction_id,
        user=current_user,
    )
    return history


@router.post("/auto-detect")
async def auto_detect_and_merge_duplicates(
    dry_run: bool = True,
    date_window_days: int = 3,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-detect and optionally merge duplicate transactions.

    Set dry_run=False to actually perform merges.
    """
    matches = await transaction_merge_service.auto_detect_and_merge_duplicates(
        db=db,
        user=current_user,
        date_window_days=date_window_days,
        dry_run=dry_run,
    )

    return {
        "dry_run": dry_run,
        "matches_found": len(matches),
        "matches": [
            {
                "primary": match[0],
                "duplicates": match[1],
            }
            for match in matches
        ],
    }
