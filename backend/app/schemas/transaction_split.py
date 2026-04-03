"""Transaction split schemas."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionSplitBase(BaseModel):
    """Base transaction split schema."""

    amount: Decimal = Field(gt=0)
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    assigned_user_id: Optional[UUID] = None


class TransactionSplitCreate(TransactionSplitBase):
    """Schema for creating a transaction split."""


class CreateSplitsRequest(BaseModel):
    """Schema for creating multiple splits for a transaction."""

    transaction_id: UUID
    splits: List[TransactionSplitCreate]


class TransactionSplitUpdate(BaseModel):
    """Schema for updating a transaction split."""

    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    assigned_user_id: Optional[UUID] = None


class TransactionSplitResponse(TransactionSplitBase):
    """Schema for transaction split response."""

    id: UUID
    parent_transaction_id: UUID
    organization_id: UUID
    settled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemberBalanceResponse(BaseModel):
    """Settlement balance between two household members."""

    member_id: UUID
    member_name: str
    total_assigned: float  # sum of splits assigned to this member
    net_owed: float  # positive = this member owes the household; negative = household owes them


class SettleRequest(BaseModel):
    """Request body for POST /transaction-splits/settle."""

    member_id: UUID
    since: Optional[str] = None  # ISO date string YYYY-MM-DD; if omitted, all time


class SettleResponse(BaseModel):
    """Response for settlement action."""

    settled_count: int
