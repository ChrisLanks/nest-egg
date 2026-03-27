"""Charitable giving API endpoints."""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.transaction import Label, Transaction, TransactionLabel
from app.constants.financial import TAX
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Charitable Giving"])

# Standard deductions sourced from year-keyed constants
STANDARD_DEDUCTION_SINGLE = TAX.STANDARD_DEDUCTION_SINGLE
STANDARD_DEDUCTION_MFJ = TAX.STANDARD_DEDUCTION_MARRIED
QCD_ANNUAL_LIMIT = 105_000
QCD_AGE_THRESHOLD = 70  # age 70.5 — we check >= 70 as a proxy


@router.get("/labels")
async def list_charitable_labels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all labels for this org so the frontend can let the user pick charitable ones."""
    result = await db.execute(
        select(Label)
        .where(Label.organization_id == current_user.organization_id)
        .order_by(Label.name)
    )
    labels = result.scalars().all()
    return [
        {"id": str(lbl.id), "name": lbl.name, "color": lbl.color, "is_income": lbl.is_income}
        for lbl in labels
    ]


@router.get("/donations")
async def get_donations(
    label_ids: Optional[str] = Query(None, description="Comma-separated label UUIDs to filter on"),
    year: Optional[int] = Query(None),
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return transactions tagged with the selected charitable labels."""
    if not label_ids:
        return {"donations": [], "ytd_total": 0.0, "year": year or 2026}

    ids = [UUID(lid.strip()) for lid in label_ids.split(",") if lid.strip()]
    if not ids:
        return {"donations": [], "ytd_total": 0.0, "year": year or 2026}

    effective_year = year or 2026

    stmt = (
        select(Transaction)
        .join(TransactionLabel, TransactionLabel.transaction_id == Transaction.id)
        .join(Account, Account.id == Transaction.account_id)
        .where(
            Account.organization_id == current_user.organization_id,
            TransactionLabel.label_id.in_(ids),
            func.extract("year", Transaction.date) == effective_year,
            Transaction.amount < 0,  # expenses are negative
        )
        .order_by(Transaction.date.desc())
    )
    if user_id:
        stmt = stmt.where(Account.user_id == user_id)

    result = await db.execute(stmt)
    txns = result.scalars().all()

    donations = [
        {
            "id": str(t.id),
            "date": t.date.isoformat() if t.date else None,
            "description": t.merchant_name or t.description or "",
            "amount": abs(float(t.amount)),
            "account_id": str(t.account_id),
            "notes": t.notes,
        }
        for t in txns
    ]
    ytd_total = sum(d["amount"] for d in donations)

    return {
        "donations": donations,
        "ytd_total": round(ytd_total, 2),
        "year": effective_year,
    }


@router.get("/bunching-analysis")
async def bunching_analysis(
    annual_giving: float = Query(..., gt=0, description="Expected annual charitable giving"),
    marginal_rate: float = Query(..., ge=0, le=1, description="Marginal federal tax rate as decimal"),
    filing_status: str = Query("single", description="single or mfj"),
    current_user: User = Depends(get_current_user),
):
    """Compare annual giving vs bunching (2-year) strategy tax savings."""
    std_ded = STANDARD_DEDUCTION_MFJ if filing_status == "mfj" else STANDARD_DEDUCTION_SINGLE

    # Annual strategy: itemize if giving > std deduction, else no benefit
    annual_itemized = annual_giving
    annual_benefit_per_year = max(0.0, annual_itemized - std_ded) * marginal_rate

    # Bunching: give 2x in year 1 (itemize), std deduction in year 2
    bunched_amount = annual_giving * 2
    bunched_year1_benefit = max(0.0, bunched_amount - std_ded) * marginal_rate
    bunched_year2_benefit = 0.0  # take standard deduction
    bunched_avg_per_year = (bunched_year1_benefit + bunched_year2_benefit) / 2

    return {
        "standard_deduction": std_ded,
        "filing_status": filing_status,
        "annual_giving": annual_giving,
        "annual_strategy": {
            "itemized_amount": annual_itemized,
            "tax_savings_per_year": round(annual_benefit_per_year, 2),
            "two_year_savings": round(annual_benefit_per_year * 2, 2),
        },
        "bunching_strategy": {
            "year1_giving": bunched_amount,
            "year1_tax_savings": round(bunched_year1_benefit, 2),
            "year2_giving": 0.0,
            "year2_tax_savings": 0.0,
            "avg_annual_savings": round(bunched_avg_per_year, 2),
            "two_year_savings": round(bunched_year1_benefit, 2),
        },
        "bunching_advantage": round(
            bunched_year1_benefit - annual_benefit_per_year * 2, 2
        ),
    }


@router.get("/qcd-opportunity")
async def qcd_opportunity(
    user_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return IRA balance eligible for QCD and eligibility info."""
    from sqlalchemy import cast, String

    ira_types = ["retirement_ira", "retirement_sep_ira", "retirement_simple_ira"]
    stmt = select(
        func.sum(Account.current_balance).label("total_ira")
    ).where(
        Account.organization_id == current_user.organization_id,
        cast(Account.account_type, String).in_(ira_types),
    )
    if user_id:
        stmt = stmt.where(Account.user_id == user_id)

    result = await db.execute(stmt)
    total_ira = float(result.scalar() or 0)

    return {
        "qcd_annual_limit": QCD_ANNUAL_LIMIT,
        "ira_balance": round(total_ira, 2),
        "eligible_for_qcd": None,  # requires birthdate — not in scope yet
        "age_required": QCD_AGE_THRESHOLD,
        "note": "QCDs require age 70.5+. Connect a Traditional IRA and add birthdate to check eligibility.",
    }
