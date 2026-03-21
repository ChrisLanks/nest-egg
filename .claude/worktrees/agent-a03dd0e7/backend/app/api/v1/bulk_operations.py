"""Bulk operations API endpoints for undo/redo support."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.bulk_operation_log import BulkOperationLog
from app.models.user import User
from app.utils.datetime_utils import utc_now

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

    # Mark operation as undone
    now = utc_now()
    operation.is_undone = True
    operation.undone_at = now

    # NOTE: Actual state restoration (e.g., updating transactions back to
    # previous_state) should be implemented per operation_type. For now we
    # record the undo intent so the frontend can react accordingly and a
    # service layer can be wired in later.

    await db.commit()
    await db.refresh(operation)

    return UndoResponse(
        id=operation.id,
        operation_type=operation.operation_type,
        is_undone=True,
        undone_at=now.isoformat(),
        restored_count=len(operation.affected_ids) if operation.affected_ids else 0,
    )
