"""W-4 / Withholding optimizer API endpoint."""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.constants.financial import TAX, VARIABLE_INCOME
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(tags=["Withholding Check"])


class WithholdingCheckRequest(BaseModel):
    filing_status: str = Field("single", description="single or married")
    annual_salary: float = Field(..., gt=0)
    ytd_withheld: float = Field(0, ge=0, description="Year-to-date federal tax withheld")
    months_remaining: int = Field(..., ge=0, le=12, description="Months remaining in tax year")
    other_income: float = Field(0, ge=0, description="Investment, freelance, etc.")
    capital_gains_expected: float = Field(0, ge=0)
    ira_contributions: float = Field(0, ge=0)
    prior_year_tax: Optional[float] = Field(None, ge=0, description="Prior year total tax liability")
    year: Optional[int] = Field(None)


class WithholdingCheckResponse(BaseModel):
    projected_tax: float
    safe_harbour_amount: float
    ytd_withheld: float
    projected_year_end_withholding: float
    underpayment_risk: bool
    recommended_additional_withholding_per_paycheck: float
    w4_extra_amount: float
    notes: list
    tax_year: int


def _bracket_tax(taxable_income: float, filing_status: str, year: int) -> float:
    """Compute federal income tax from brackets."""
    if taxable_income <= 0:
        return 0.0
    tax_data = TAX.for_year(year)
    key = "BRACKETS_MARRIED" if filing_status.lower() in ("married", "mfj") else "BRACKETS_SINGLE"
    brackets = tax_data[key]
    total = 0.0
    prev = 0.0
    for rate, ceiling in brackets:
        if taxable_income <= prev:
            break
        in_bracket = min(taxable_income, ceiling) - prev
        if in_bracket > 0:
            total += in_bracket * rate
        prev = ceiling
    return round(total, 2)


@router.post("/withholding-check", response_model=WithholdingCheckResponse)
async def withholding_check(
    request: WithholdingCheckRequest,
    current_user: User = Depends(get_current_user),
):
    """Project full-year tax liability and check if withholding meets safe harbour."""
    year = request.year or datetime.date.today().year
    filing_status = request.filing_status.lower()
    married = filing_status in ("married", "mfj")
    tax_data = TAX.for_year(year)

    std_ded = tax_data["STANDARD_DEDUCTION_MARRIED"] if married else tax_data["STANDARD_DEDUCTION_SINGLE"]

    total_income = request.annual_salary + request.other_income + request.capital_gains_expected
    deductions = std_ded + request.ira_contributions
    taxable = max(0, total_income - deductions)

    projected_tax = _bracket_tax(taxable, filing_status, year)

    # Safe harbour: min(90% of current year, 110% of prior year if AGI > $150K else 100%)
    if request.prior_year_tax is not None and request.prior_year_tax > 0:
        prior_factor = float(
            VARIABLE_INCOME.SAFE_HARBOR_RATE_HIGH_INCOME
            if total_income > VARIABLE_INCOME.SAFE_HARBOR_110_PCT_INCOME_THRESHOLD
            else VARIABLE_INCOME.SAFE_HARBOR_RATE_NORMAL
        )
        safe_harbour = min(
            projected_tax * float(VARIABLE_INCOME.SAFE_HARBOR_CURRENT_YEAR_RATE),
            request.prior_year_tax * prior_factor,
        )
    else:
        safe_harbour = projected_tax * float(VARIABLE_INCOME.SAFE_HARBOR_CURRENT_YEAR_RATE)

    # Project year-end withholding
    months_elapsed = 12 - request.months_remaining
    if months_elapsed > 0:
        monthly_withholding = request.ytd_withheld / months_elapsed
    else:
        monthly_withholding = 0
    projected_year_end = request.ytd_withheld + monthly_withholding * request.months_remaining

    underpayment_risk = projected_year_end < safe_harbour

    # Recommended additional per paycheck (assume biweekly = 26 paychecks)
    remaining_paychecks = max(1, request.months_remaining * 2)  # rough biweekly estimate
    shortfall = max(0, safe_harbour - projected_year_end)
    per_paycheck = round(shortfall / remaining_paychecks, 2) if remaining_paychecks > 0 else 0

    notes = []
    if underpayment_risk:
        notes.append(
            f"Projected withholding (${projected_year_end:,.0f}) falls short of "
            f"safe harbour (${safe_harbour:,.0f}) by ${shortfall:,.0f}."
        )
        notes.append(
            f"Add ${per_paycheck:,.0f} per paycheck on W-4 Line 4(c) to avoid penalty."
        )
    else:
        notes.append("Your withholding appears sufficient to meet safe harbour requirements.")

    if request.capital_gains_expected > 0:
        notes.append(
            "Capital gains are not withheld from — consider quarterly estimated payments."
        )

    return WithholdingCheckResponse(
        projected_tax=projected_tax,
        safe_harbour_amount=round(safe_harbour, 2),
        ytd_withheld=request.ytd_withheld,
        projected_year_end_withholding=round(projected_year_end, 2),
        underpayment_risk=underpayment_risk,
        recommended_additional_withholding_per_paycheck=per_paycheck,
        w4_extra_amount=round(shortfall, 2),
        notes=notes,
        tax_year=year,
    )
