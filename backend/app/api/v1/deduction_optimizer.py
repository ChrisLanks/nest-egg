"""Itemized vs Standard Deduction Optimizer API endpoint."""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.constants.financial import TAX
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(tags=["Deduction Optimizer"])


class DeductionOptimizerRequest(BaseModel):
    filing_status: str = Field("single", description="single or married")
    mortgage_interest: float = Field(0, ge=0)
    state_local_taxes: float = Field(0, ge=0, description="State and local taxes paid (SALT)")
    charitable_cash: float = Field(0, ge=0)
    charitable_noncash: float = Field(0, ge=0)
    medical_expenses: float = Field(0, ge=0)
    agi: float = Field(0, ge=0, description="Adjusted gross income")
    year: Optional[int] = Field(None, description="Tax year; defaults to current year")


class DeductionOptimizerResponse(BaseModel):
    standard_deduction: float
    itemized_total: float
    salt_capped: float
    medical_deductible: float
    difference: float
    recommendation: str
    breakeven_mortgage_interest: float
    tax_year: int
    salt_cap_note: Optional[str] = None


@router.post("/deduction-optimizer", response_model=DeductionOptimizerResponse)
async def optimize_deductions(
    request: DeductionOptimizerRequest,
    current_user: User = Depends(get_current_user),
):
    """Compare standard vs itemized deductions and recommend the better option."""
    year = request.year or datetime.date.today().year
    tax_data = TAX.for_year(year)
    married = request.filing_status.lower() in ("married", "mfj")

    standard = tax_data["STANDARD_DEDUCTION_MARRIED"] if married else tax_data["STANDARD_DEDUCTION_SINGLE"]

    # SALT cap — year-resolved (OBBBA 2025 raised to $40K for 2025-2028)
    salt_cap = TAX.salt_cap_for_year(year)
    salt_phaseout = TAX.salt_cap_phaseout_for_year(year)

    # Apply phase-out if AGI exceeds threshold
    effective_salt_cap = salt_cap
    if salt_phaseout and request.agi > salt_phaseout:
        # Reduce cap by 30% for every $10K over the phase-out start
        reduction_pct = min(1.0, 0.30 * ((request.agi - salt_phaseout) / 10_000))
        effective_salt_cap = round(salt_cap * (1 - reduction_pct), 2)

    salt_capped = min(request.state_local_taxes, effective_salt_cap)

    # Medical deductible portion: only amount exceeding 7.5% of AGI
    medical_deductible = max(0, request.medical_expenses - request.agi * 0.075) if request.agi > 0 else 0

    itemized_total = (
        salt_capped
        + request.mortgage_interest
        + request.charitable_cash
        + request.charitable_noncash
        + medical_deductible
    )

    difference = itemized_total - standard

    if difference > 0:
        recommendation = (
            f"Itemize: you save ${difference:,.0f} more than the standard deduction."
        )
    elif difference == 0:
        recommendation = "Either option is equal. Standard deduction is simpler."
    else:
        recommendation = (
            f"Take the standard deduction: it saves ${abs(difference):,.0f} more than itemizing."
        )

    # How much more mortgage interest needed to make itemizing worthwhile
    current_non_mortgage = salt_capped + request.charitable_cash + request.charitable_noncash + medical_deductible
    breakeven = max(0, standard - current_non_mortgage)

    # Build SALT cap note
    if salt_cap > 10_000:
        salt_cap_note = f"SALT cap is ${salt_cap:,} for {year} (phase-out above ${salt_phaseout:,} AGI)" if salt_phaseout else f"SALT cap is ${salt_cap:,} for {year}"
    else:
        salt_cap_note = f"SALT cap is ${salt_cap:,} for {year} (TCJA)"

    return DeductionOptimizerResponse(
        standard_deduction=standard,
        itemized_total=round(itemized_total, 2),
        salt_capped=salt_capped,
        medical_deductible=round(medical_deductible, 2),
        difference=round(difference, 2),
        recommendation=recommendation,
        breakeven_mortgage_interest=round(breakeven, 2),
        tax_year=year,
        salt_cap_note=salt_cap_note,
    )
