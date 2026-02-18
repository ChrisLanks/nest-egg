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


class TransactionSplitResponse(TransactionSplitBase):
    """Schema for transaction split response."""

    id: UUID
    parent_transaction_id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
