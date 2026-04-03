"""Transaction schemas."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


_MAX_TRANSACTION_AMOUNT = Decimal("999999999.99")  # $999M — covers any personal finance amount


class TransactionBase(BaseModel):
    """Base transaction schema."""

    date: date
    amount: Decimal = Field(
        ...,
        ge=-_MAX_TRANSACTION_AMOUNT,
        le=_MAX_TRANSACTION_AMOUNT,
        description="Transaction amount in account currency. Negative = debit, positive = credit.",
    )
    merchant_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=255)
    category_primary: Optional[str] = None
    category_detailed: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Transaction creation schema."""

    account_id: UUID
    external_transaction_id: Optional[str] = None
    is_pending: bool = False


class ManualTransactionCreate(TransactionBase):
    """Schema for manually created transactions (no external IDs, no dedup hash)."""

    account_id: UUID
    category_id: Optional[UUID] = None
    is_pending: bool = False
    is_transfer: bool = False
    notes: Optional[str] = Field(None, max_length=10000)
    flagged_for_review: bool = False

    @field_validator("date")
    @classmethod
    def validate_date_not_too_far_future(cls, v: date) -> date:
        """Warn if date is more than 1 year in the future (cap accepted at year 2100)."""
        from datetime import date as date_type
        if v > date_type(2100, 1, 1):
            raise ValueError("date must be on or before 2100-01-01")
        return v


class TransactionUpdate(BaseModel):
    """Transaction update schema."""

    merchant_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=255)
    category_primary: Optional[str] = None
    is_transfer: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=10000)
    flagged_for_review: Optional[bool] = None


class LabelSummary(BaseModel):
    """Label summary for transaction lists."""

    id: UUID
    name: str
    color: Optional[str] = None
    is_income: bool

    model_config = {"from_attributes": True}


class CategorySummary(BaseModel):
    """Category summary for transaction display."""

    id: UUID
    name: str
    color: Optional[str] = None
    parent_id: Optional[UUID] = None
    parent_name: Optional[str] = None

    model_config = {"from_attributes": True}


class Transaction(TransactionBase):
    """Transaction response schema."""

    id: UUID
    organization_id: UUID
    account_id: UUID
    external_transaction_id: Optional[str] = None
    is_pending: bool
    is_transfer: bool
    is_split: bool = False
    notes: Optional[str] = None
    flagged_for_review: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionDetail(Transaction):
    """Transaction with related data."""

    account_name: Optional[str] = None
    account_mask: Optional[str] = None
    category: Optional[CategorySummary] = None
    labels: List[LabelSummary] = []

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    """Paginated transaction list response."""

    transactions: List[TransactionDetail]
    total: int
    page: int
    page_size: int
    has_more: bool
    next_cursor: Optional[str] = None  # Cursor for next page


class CategoryCreate(BaseModel):
    """Category creation schema."""

    name: str
    color: Optional[str] = None
    parent_category_id: Optional[UUID] = None
    plaid_category_name: Optional[str] = None  # Link to provider category for auto-mapping

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate category name."""
        # Strip whitespace
        v = v.strip()

        # Check for empty
        if not v:
            raise ValueError("Category name cannot be empty")

        # Check length
        if len(v) > 100:
            raise ValueError("Category name must be 100 characters or less")

        # Check for dangerous characters (prevent XSS)
        if "<" in v or ">" in v:
            raise ValueError("Category name cannot contain < or > characters")

        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is valid hex code."""
        if v is None:
            return v

        # Strip whitespace and hash
        v = v.strip().lstrip("#")

        # Validate hex format (3 or 6 characters)
        if not re.match(r"^[0-9A-Fa-f]{3}$|^[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be valid hex code (e.g., #FF0000 or #F00)")

        # Return with hash prefix
        return f"#{v}"


class CategoryUpdate(BaseModel):
    """Category update schema."""

    name: Optional[str] = None
    color: Optional[str] = None
    parent_category_id: Optional[UUID] = None
    plaid_category_name: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate category name."""
        if v is None:
            return v

        # Strip whitespace
        v = v.strip()

        # Check for empty
        if not v:
            raise ValueError("Category name cannot be empty")

        # Check length
        if len(v) > 100:
            raise ValueError("Category name must be 100 characters or less")

        # Check for dangerous characters (prevent XSS)
        if "<" in v or ">" in v:
            raise ValueError("Category name cannot contain < or > characters")

        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is valid hex code."""
        if v is None:
            return v

        # Strip whitespace and hash
        v = v.strip().lstrip("#")

        # Validate hex format (3 or 6 characters)
        if not re.match(r"^[0-9A-Fa-f]{3}$|^[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be valid hex code (e.g., #FF0000 or #F00)")

        # Return with hash prefix
        return f"#{v}"


class CategoryResponse(BaseModel):
    """Category response schema."""

    id: Optional[UUID] = None  # None for provider categories not yet in DB
    organization_id: UUID
    name: str
    color: Optional[str] = None
    parent_category_id: Optional[UUID] = None
    plaid_category_name: Optional[str] = None  # Linked provider category
    is_custom: bool = True  # False for provider categories from transactions
    transaction_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LabelCreate(BaseModel):
    """Label creation schema."""

    name: str
    color: Optional[str] = None
    is_income: bool = False
    parent_label_id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate label name."""
        # Strip whitespace
        v = v.strip()

        # Check for empty
        if not v:
            raise ValueError("Label name cannot be empty")

        # Check length
        if len(v) > 100:
            raise ValueError("Label name must be 100 characters or less")

        # Check for dangerous characters (prevent XSS)
        if "<" in v or ">" in v:
            raise ValueError("Label name cannot contain < or > characters")

        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is valid hex code."""
        if v is None:
            return v

        # Strip whitespace and hash
        v = v.strip().lstrip("#")

        # Validate hex format (3 or 6 characters)
        if not re.match(r"^[0-9A-Fa-f]{3}$|^[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be valid hex code (e.g., #FF0000 or #F00)")

        # Return with hash prefix
        return f"#{v}"


class LabelUpdate(BaseModel):
    """Label update schema."""

    name: Optional[str] = None
    color: Optional[str] = None
    is_income: Optional[bool] = None
    parent_label_id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate label name."""
        if v is None:
            return v

        # Strip whitespace
        v = v.strip()

        # Check for empty
        if not v:
            raise ValueError("Label name cannot be empty")

        # Check length
        if len(v) > 100:
            raise ValueError("Label name must be 100 characters or less")

        # Check for dangerous characters (prevent XSS)
        if "<" in v or ">" in v:
            raise ValueError("Label name cannot contain < or > characters")

        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is valid hex code."""
        if v is None:
            return v

        # Strip whitespace and hash
        v = v.strip().lstrip("#")

        # Validate hex format (3 or 6 characters)
        if not re.match(r"^[0-9A-Fa-f]{3}$|^[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be valid hex code (e.g., #FF0000 or #F00)")

        # Return with hash prefix
        return f"#{v}"


class LabelResponse(BaseModel):
    """Label response schema."""

    id: UUID
    organization_id: UUID
    name: str
    color: Optional[str] = None
    is_income: bool
    parent_label_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
