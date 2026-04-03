"""Loan modeling API endpoints — pure computation, no DB session needed."""

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.dependencies import get_current_user
from app.services.rate_limit_service import rate_limit_service
from app.models.user import User
from app.services.loan_modeling_service import LoanModelingService

logger = logging.getLogger(__name__)



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(tags=["Loan Modeling"], dependencies=[Depends(_rate_limit)])


@router.get("/calculate")
async def calculate_loan(
    principal: float = Query(..., gt=0, description="Loan principal amount"),
    annual_rate: float = Query(..., ge=0, le=1, description="Annual interest rate as decimal (e.g. 0.065 for 6.5%)"),
    term_months: int = Query(..., gt=0, le=600, description="Loan term in months"),
    annual_gross_income: float = Query(..., gt=0, description="Gross annual income"),
    existing_monthly_debt: float = Query(0.0, ge=0, description="Existing monthly debt payments"),
    current_user: User = Depends(get_current_user),
):
    """Calculate monthly payment, DTI impact, and net worth impact for a loan."""
    svc = LoanModelingService()
    p = Decimal(str(principal))
    r = Decimal(str(annual_rate))
    income = Decimal(str(annual_gross_income))
    existing_debt = Decimal(str(existing_monthly_debt))

    monthly_payment = svc.calculate_monthly_payment(p, r, term_months)
    dti = svc.calculate_dti_impact(income, existing_debt, monthly_payment)

    total_paid = float(monthly_payment) * term_months
    total_interest = total_paid - principal

    monthly_income = annual_gross_income / 12
    monthly_surplus_before = monthly_income - float(existing_debt)
    monthly_surplus_after = monthly_income - float(existing_debt) - float(monthly_payment)

    return {
        "monthly_payment": float(monthly_payment),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
        "dti": dti,
        "net_worth_impact": {
            "debt_added": principal,
            "monthly_cash_flow_before": round(monthly_surplus_before, 2),
            "monthly_cash_flow_after": round(monthly_surplus_after, 2),
            "cash_flow_delta": round(monthly_surplus_after - monthly_surplus_before, 2),
            "total_interest_cost": round(total_interest, 2),
        },
    }


@router.get("/amortization")
async def get_amortization_schedule(
    principal: float = Query(..., gt=0),
    annual_rate: float = Query(..., ge=0, le=1),
    term_months: int = Query(..., gt=0, le=600),
    current_user: User = Depends(get_current_user),
):
    """Return full amortization schedule, aggregated by year."""
    svc = LoanModelingService()
    schedule = svc.generate_amortization_schedule(
        Decimal(str(principal)),
        Decimal(str(annual_rate)),
        term_months,
    )

    # Aggregate monthly rows into annual summaries
    years: dict[int, dict] = {}
    for row in schedule:
        year = (row["month"] - 1) // 12 + 1
        if year not in years:
            years[year] = {
                "year": year,
                "principal_paid": 0.0,
                "interest_paid": 0.0,
                "ending_balance": 0.0,
            }
        years[year]["principal_paid"] = round(years[year]["principal_paid"] + row["principal"], 2)
        years[year]["interest_paid"] = round(years[year]["interest_paid"] + row["interest"], 2)
        years[year]["ending_balance"] = round(row["balance"], 2)

    annual = sorted(years.values(), key=lambda x: x["year"])

    # Add cumulative interest column
    cum = 0.0
    for row in annual:
        cum = round(cum + row["interest_paid"], 2)
        row["cumulative_interest"] = cum

    return {"schedule": annual, "months": schedule}


@router.get("/buy-vs-lease")
async def buy_vs_lease(
    vehicle_price: float = Query(..., gt=0),
    down_payment: float = Query(0.0, ge=0),
    loan_rate: float = Query(..., ge=0, le=1, description="Annual loan rate as decimal"),
    loan_term_months: int = Query(..., gt=0, le=120),
    lease_monthly: float = Query(..., gt=0),
    lease_term_months: int = Query(..., gt=0, le=60),
    residual_value_pct: float = Query(0.55, ge=0, le=1, description="Residual value as fraction of purchase price"),
    current_user: User = Depends(get_current_user),
):
    """Compare total cost of buying vs leasing a vehicle."""
    svc = LoanModelingService()
    result = svc.buy_vs_lease(
        vehicle_price=Decimal(str(vehicle_price)),
        down_payment=Decimal(str(down_payment)),
        loan_rate=Decimal(str(loan_rate)),
        loan_term_months=loan_term_months,
        lease_monthly=Decimal(str(lease_monthly)),
        lease_term_months=lease_term_months,
        residual_value_pct=Decimal(str(residual_value_pct)),
    )
    return result
