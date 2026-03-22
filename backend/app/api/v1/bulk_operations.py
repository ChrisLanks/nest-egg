"""Bulk operations API endpoints for undo/redo support."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.bulk_operation_log import BulkOperationLog
from app.models.transaction import Transaction
from app.models.user import User
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Schemas ---


class BulkOperationResponse(BaseModel):
    """Response schema for a bulk operation log entry."""

    id: UUID
    organization_id: UUID
    user_id: UUID
    operation_type: str
    affected_ids: list
    previous_state: dict | list
    new_state: dict | list | None
    is_undone: bool
    created_at: str
    undone_at: str | None

    model_config = {"from_attributes": True}


class UndoResponse(BaseModel):
    """Response schema for an undo operation."""

    id: UUID
    operation_type: str
    is_undone: bool
    undone_at: str
    restored_count: int


# --- Endpoints ---


@router.get("/", response_model=List[BulkOperationResponse])
async def list_bulk_operations(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recent bulk operations for the current user's organization."""
    result = await db.execute(
        select(BulkOperationLog)
        .where(
            BulkOperationLog.organization_id == current_user.organization_id,
            BulkOperationLog.user_id == current_user.id,
        )
        .order_by(BulkOperationLog.created_at.desc())
        .limit(limit)
    )
    operations = result.scalars().all()

    return [
        BulkOperationResponse(
            id=op.id,
            organization_id=op.organization_id,
            user_id=op.user_id,
            operation_type=op.operation_type,
            affected_ids=op.affected_ids,
            previous_state=op.previous_state,
            new_state=op.new_state,
            is_undone=op.is_undone,
            created_at=op.created_at.isoformat(),
            undone_at=op.undone_at.isoformat() if op.undone_at else None,
        )
        for op in operations
    ]


@router.post("/{operation_id}/undo", response_model=UndoResponse)
async def undo_bulk_operation(
    operation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Undo a bulk operation by restoring the previous state.

    Only the user who performed the operation can undo it.
    An operation can only be undone once.
    """
    # Fetch the operation
    result = await db.execute(
        select(BulkOperationLog).where(
            BulkOperationLog.id == operation_id,
            BulkOperationLog.organization_id == current_user.organization_id,
            BulkOperationLog.user_id == current_user.id,
        )
    )
    operation = result.scalar_one_or_none()

    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk operation not found",
        )

    if operation.is_undone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This operation has already been undone",
        )

    # Restore previous state per operation type
    restored_count = await _restore_previous_state(db, operation, current_user)

    # Mark operation as undone
    now = utc_now()
    operation.is_undone = True
    operation.undone_at = now

    await db.commit()
    await db.refresh(operation)

    return UndoResponse(
        id=operation.id,
        operation_type=operation.operation_type,
        is_undone=True,
        undone_at=now.isoformat(),
        restored_count=restored_count,
    )


# Mutable transaction fields that can be restored from previous_state.
_RESTORABLE_FIELDS = {
    "category_id",
    "notes",
    "merchant_name",
    "flagged_for_review",
    "is_transfer",
    "is_hidden",
}


async def _restore_previous_state(
    db: AsyncSession,
    operation: BulkOperationLog,
    current_user: User,
) -> int:
    """Apply previous_state back to the affected rows.

    Supports any operation whose previous_state is a list of per-transaction
    dicts (e.g. bulk_categorize, bulk_update) or a plain dict with a single
    set of values applied to all affected_ids (e.g. bulk_delete stub).

    Returns the number of transactions restored.
    """
    previous_state = operation.previous_state
    affected_ids = operation.affected_ids or []

    if not previous_state or not affected_ids:
        logger.warning(
            "undo_skipped_no_state",
            extra={"operation_id": str(operation.id), "type": operation.operation_type},
        )
        return 0

    org_id = operation.organization_id

    # previous_state may be a list (one entry per transaction) or a dict
    # (single set of values applied to all affected_ids).
    if isinstance(previous_state, list):
        # Each entry: {"id": "<uuid>", "category_id": ..., ...}
        restore_map = {str(entry["id"]): entry for entry in previous_state if "id" in entry}
        restored = 0
        for txn_id_str, prev in restore_map.items():
            patch = {k: prev.get(k) for k in _RESTORABLE_FIELDS if k in prev}
            if not patch:
                continue
            result = await db.execute(
                update(Transaction)
                .where(
                    Transaction.id == txn_id_str,
                    Transaction.organization_id == org_id,
                )
                .values(**patch)
            )
            restored += result.rowcount
        return restored

    if isinstance(previous_state, dict):
        # Single dict applied to all affected_ids
        patch = {k: previous_state.get(k) for k in _RESTORABLE_FIELDS if k in previous_state}
        if not patch:
            return 0
        result = await db.execute(
            update(Transaction)
            .where(
                Transaction.id.in_(affected_ids),
                Transaction.organization_id == org_id,
            )
            .values(**patch)
        )
        return result.rowcount

    return 0
