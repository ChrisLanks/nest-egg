"""AMT (Alternative Minimum Tax) exposure calculator API endpoint."""

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.constants.financial import AMT, TAX
from app.dependencies import get_current_user
from app.services.rate_limit_service import rate_limit_service
from app.models.user import User



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(tags=["AMT Calculator"], dependencies=[Depends(_rate_limit)])


class AmtExposureRequest(BaseModel):
    ordinary_income: float = Field(..., ge=0)
    filing_status: str = Field("single", description="single or married")
    capital_gains: float = Field(0, ge=0)
    iso_exercises: float = Field(0, ge=0, description="ISO bargain element (FMV - strike) * shares")
    deductions_at_risk: float = Field(0, ge=0, description="State taxes paid + misc deductions disallowed under AMT")
    year: Optional[int] = Field(None, description="Tax year; defaults to current year")


class AmtExposureResponse(BaseModel):
    regular_tax: float
    tentative_minimum_tax: float
    amt_owed: float
    at_risk: bool
    exemption_used: float
    notes: List[str]
    tax_year: int


def _bracket_tax(taxable_income: float, filing_status: str, year: int) -> float:
    """Compute regular federal income tax from brackets."""
    if taxable_income <= 0:
        return 0.0
    tax_data = TAX.for_year(year)
    key = "BRACKETS_MARRIED" if filing_status.lower() in ("married", "mfj") else "BRACKETS_SINGLE"
    brackets = tax_data[key]
    total_tax = 0.0
    prev = 0.0
    for rate, ceiling in brackets:
        if taxable_income <= prev:
            break
        in_bracket = min(taxable_income, ceiling) - prev
        if in_bracket > 0:
            total_tax += in_bracket * rate
        prev = ceiling
    return round(total_tax, 2)


@router.post("/amt-exposure", response_model=AmtExposureResponse)
async def calculate_amt_exposure(
    request: AmtExposureRequest,
    current_user: User = Depends(get_current_user),
):
    """Calculate AMT exposure including ISO exercise impact."""
    year = request.year or datetime.date.today().year
    filing_status = request.filing_status.lower()
    married = filing_status in ("married", "mfj")

    amt_data = AMT.for_year(year)
    tax_data = TAX.for_year(year)

    std_ded = tax_data["STANDARD_DEDUCTION_MARRIED"] if married else tax_data["STANDARD_DEDUCTION_SINGLE"]

    # Regular tax
    regular_taxable = max(0, request.ordinary_income - std_ded)
    regular_tax = _bracket_tax(regular_taxable, filing_status, year)

    # AMT income: add back ISO exercises and disallowed deductions
    amti = request.ordinary_income + request.iso_exercises + request.deductions_at_risk

    # AMT exemption with phase-out
    exemption = amt_data["AMT_EXEMPTION_MARRIED"] if married else amt_data["AMT_EXEMPTION_SINGLE"]
    phaseout_start = amt_data["AMT_PHASEOUT_MARRIED"] if married else amt_data["AMT_PHASEOUT_SINGLE"]
    if amti > phaseout_start:
        exemption_reduction = (amti - phaseout_start) * 0.25
        exemption = max(0, exemption - exemption_reduction)

    amt_taxable = max(0, amti - exemption)

    # AMT: 26% up to threshold, 28% above
    rate_26_threshold = amt_data["AMT_RATE_26_THRESHOLD"]
    if amt_taxable <= rate_26_threshold:
        tmt = amt_taxable * 0.26
    else:
        tmt = rate_26_threshold * 0.26 + (amt_taxable - rate_26_threshold) * 0.28
    tmt = round(tmt, 2)

    amt_owed = round(max(0, tmt - regular_tax), 2)

    notes = []
    if request.iso_exercises > 0:
        notes.append(
            f"ISO bargain element of ${request.iso_exercises:,.0f} is added to AMT income."
        )
    if amt_owed > 0:
        notes.append(
            f"You owe ${amt_owed:,.0f} in AMT above your regular tax of ${regular_tax:,.0f}."
        )
    else:
        notes.append("No AMT exposure — regular tax exceeds tentative minimum tax.")
    if exemption < (amt_data["AMT_EXEMPTION_MARRIED"] if married else amt_data["AMT_EXEMPTION_SINGLE"]):
        notes.append("AMT exemption was partially phased out due to high income.")

    return AmtExposureResponse(
        regular_tax=regular_tax,
        tentative_minimum_tax=tmt,
        amt_owed=amt_owed,
        at_risk=amt_owed > 0,
        exemption_used=round(exemption, 2),
        notes=notes,
        tax_year=year,
    )
