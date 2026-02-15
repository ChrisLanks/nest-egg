"""RMD (Required Minimum Distribution) schemas."""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AccountRMD(BaseModel):
    """RMD details for a single retirement account."""

    account_id: UUID
    account_name: str
    account_type: str
    account_balance: Decimal
    required_distribution: Decimal
    distribution_taken: Decimal  # Amount already withdrawn this year
    remaining_required: Decimal  # Amount still required this year


class RMDSummary(BaseModel):
    """RMD summary for all retirement accounts."""

    user_age: int
    requires_rmd: bool
    rmd_deadline: Optional[date] = None  # December 31 of current year
    total_required_distribution: Decimal
    total_distribution_taken: Decimal
    total_remaining_required: Decimal
    accounts: list[AccountRMD]
    penalty_if_missed: Optional[Decimal] = None  # 25% of shortfall
