"""Transaction merges API endpoints."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.transaction_merge import (
    TransactionMergeRequest,
    TransactionMergeResponse,
    DuplicateDetectionRequest,
)
from app.services.rate_limit_service import rate_limit_service
from app.services.transaction_merge_service import transaction_merge_service


class FindDuplicatesResponse(BaseModel):
    transaction_id: UUID
    potential_duplicates: List[Any]
    count: int


class AutoDetectResponse(BaseModel):
    dry_run: bool
    matches_found: int
    matches: List[Dict[str, Any]]


async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )


router = APIRouter(dependencies=[Depends(_rate_limit)])


@router.post("/find-duplicates", response_model=FindDuplicatesResponse)
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

    return FindDuplicatesResponse(
        transaction_id=request.transaction_id,
        potential_duplicates=duplicates,
        count=len(duplicates),
    )


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


@router.post("/auto-detect", response_model=AutoDetectResponse)
async def auto_detect_and_merge_duplicates(
    http_request: Request,
    dry_run: bool = True,
    date_window_days: int = 3,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-detect and optionally merge duplicate transactions.

    Set dry_run=False to actually perform merges.
    """
    # Tighter limit for this potentially expensive auto-detect operation
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=60,
        identifier=str(current_user.id),
    )
    matches = await transaction_merge_service.auto_detect_and_merge_duplicates(
        db=db,
        user=current_user,
        date_window_days=date_window_days,
        dry_run=dry_run,
    )

    return AutoDetectResponse(
        dry_run=dry_run,
        matches_found=len(matches),
        matches=[
            {
                "primary": match[0],
                "duplicates": match[1],
            }
            for match in matches
        ],
    )
