"""Transaction merge schemas."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DuplicateDetectionRequest(BaseModel):
    """Request schema for finding duplicates."""

    transaction_id: UUID
    date_window_days: int = Field(default=3, ge=1, le=30)
    amount_tolerance: Decimal = Field(default=Decimal("0.01"), ge=0)


class TransactionMergeRequest(BaseModel):
    """Request schema for merging transactions."""

    primary_transaction_id: UUID
    duplicate_transaction_ids: List[UUID]
    merge_reason: Optional[str] = None


class TransactionMergeResponse(BaseModel):
    """Response schema for transaction merge."""

    id: UUID
    organization_id: UUID
    primary_transaction_id: UUID
    duplicate_transaction_id: UUID
    merge_reason: Optional[str]
    is_auto_merged: bool
    merged_at: datetime
    merged_by_user_id: Optional[UUID]

    class Config:
        from_attributes = True
