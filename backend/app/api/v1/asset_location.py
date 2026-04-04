"""Asset location optimization API endpoint."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, get_filtered_accounts
from app.services.rate_limit_service import rate_limit_service
from app.models.account import Account, TaxTreatment
from app.models.holding import Holding
from app.models.user import User



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(dependencies=[Depends(_rate_limit)])


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class AssetLocationItem(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    tax_treatment: str
    ticker: Optional[str]
    asset_class: Optional[str]
    name: str
    current_value: float
    is_optimal: bool
    recommended_location: str  # "pre_tax", "roth", "taxable", "tax_free"
    reason: str


class AssetLocationResponse(BaseModel):
    items: List[AssetLocationItem]
    total_value: float
    optimal_count: int
    suboptimal_count: int
    optimization_score: float  # 0-100
    summary_tip: str


# ---------------------------------------------------------------------------
# Recommendation helpers
# ---------------------------------------------------------------------------

# Ticker-based fallback mapping when asset_class is None.
_TICKER_LOCATION: dict[str, str] = {
    # PRE_TAX: income-generating / high-turnover
    "VNQ": "pre_tax",
    "SCHD": "pre_tax",
    "BND": "pre_tax",
    "AGG": "pre_tax",
    "LQD": "pre_tax",
    "HYG": "pre_tax",
    # ROTH: highest-growth potential
    "QQQ": "roth",
    "VWO": "roth",
    "VBR": "roth",
    "ARKK": "roth",
    "VB": "roth",
    "IWM": "roth",
    # TAXABLE: tax-efficient index funds
    "VTI": "taxable",
    "FSKAX": "taxable",
    "SWTSX": "taxable",
    "SPY": "taxable",
    "IVV": "taxable",
    "VOO": "taxable",
}

_PRE_TAX_CLASSES = {"bond", "fixed_income", "tips", "reit", "dividend"}
_ROTH_CLASSES = {"small_cap", "emerging_market", "international", "growth"}
_TAXABLE_CLASSES = {"large_cap", "index", "etf", "blend"}

_TREATMENT_DISPLAY = {
    TaxTreatment.PRE_TAX: "pre_tax",
    TaxTreatment.ROTH: "roth",
    TaxTreatment.TAXABLE: "taxable",
    TaxTreatment.TAX_FREE: "tax_free",
}

_REASONS = {
    "pre_tax": "Bonds, REITs, and high-dividend assets grow most efficiently in tax-deferred accounts.",
    "roth": "High-growth assets compound tax-free in a Roth account, maximizing long-term value.",
    "taxable": "Tax-efficient index funds and ETFs are well suited for taxable brokerage accounts.",
    "tax_free": "HSA/529 accounts offer tax-free growth for qualified expenses.",
}


def _recommended_location(asset_class: Optional[str], ticker: Optional[str]) -> str:
    """Determine the recommended tax location for a holding."""
    if asset_class:
        normalized = asset_class.lower().strip()
        if normalized in _PRE_TAX_CLASSES:
            return "pre_tax"
        if normalized in _ROTH_CLASSES:
            return "roth"
        if normalized in _TAXABLE_CLASSES:
            return "taxable"
        # Partial-match fallbacks
        for key in _PRE_TAX_CLASSES:
            if key in normalized:
                return "pre_tax"
        for key in _ROTH_CLASSES:
            if key in normalized:
                return "roth"

    if ticker:
        upper = ticker.upper().strip()
        if upper in _TICKER_LOCATION:
            return _TICKER_LOCATION[upper]

    return "taxable"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/asset-location", response_model=AssetLocationResponse)
async def get_asset_location(
    user_id: Optional[str] = Query(default=None, description="Household member user ID; defaults to all org accounts"),
    user_ids: Optional[list[str]] = Query(None, description="Multi-user filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze whether holdings are optimally located across account tax treatments.

    Returns each holding with its current tax treatment, the recommended
    treatment, and whether the two match.
    """
    import uuid as _uuid

    # Resolve subject user
    subject_user_id = None
    if user_id and user_id != str(current_user.id):
        member_result = await db.execute(
            select(User).where(
                User.id == _uuid.UUID(user_id),
                User.organization_id == current_user.organization_id,
            )
        )
        member = member_result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=404, detail="Household member not found")
        subject_user_id = member.id
    elif user_id:
        subject_user_id = current_user.id

    # Fetch holdings joined to their account, scoped to this user's org.
    conditions = [
        Holding.organization_id == current_user.organization_id,
        Account.organization_id == current_user.organization_id,
        Account.is_active.is_(True),
    ]
    if subject_user_id:
        conditions.append(Account.user_id == subject_user_id)

    result = await db.execute(
        select(Holding, Account)
        .join(Account, Holding.account_id == Account.id)
        .where(and_(*conditions))
        .order_by(Account.name, Holding.ticker)
    )
    rows = result.all()

    items: List[AssetLocationItem] = []
    total_value = 0.0
    optimal_count = 0
    suboptimal_count = 0

    for holding, account in rows:
        current_value = float(holding.current_total_value or 0)
        if current_value == 0:
            continue

        # Determine current tax treatment label
        tax_treatment = account.tax_treatment
        if tax_treatment is None:
            current_location = "taxable"
        else:
            current_location = _TREATMENT_DISPLAY.get(tax_treatment, "taxable")

        recommended = _recommended_location(holding.asset_class, holding.ticker)
        is_optimal = current_location == recommended
        reason = _REASONS.get(recommended, "Review placement for tax efficiency.")

        items.append(
            AssetLocationItem(
                account_id=str(account.id),
                account_name=account.name,
                account_type=account.account_type.value,
                tax_treatment=current_location,
                ticker=holding.ticker,
                asset_class=holding.asset_class,
                name=holding.name or holding.ticker,
                current_value=current_value,
                is_optimal=is_optimal,
                recommended_location=recommended,
                reason=reason,
            )
        )

        total_value += current_value
        if is_optimal:
            optimal_count += 1
        else:
            suboptimal_count += 1

    total_count = optimal_count + suboptimal_count
    optimization_score = (optimal_count / total_count * 100.0) if total_count > 0 else 100.0

    if optimization_score < 50:
        summary_tip = (
            "Consider moving bonds/REITs to pre-tax accounts and high-growth holdings to Roth."
        )
    elif optimization_score < 80:
        summary_tip = (
            "Some reallocation could improve tax efficiency — see suboptimal items below."
        )
    else:
        summary_tip = "Your asset location is well optimized."

    return AssetLocationResponse(
        items=items,
        total_value=total_value,
        optimal_count=optimal_count,
        suboptimal_count=suboptimal_count,
        optimization_score=round(optimization_score, 1),
        summary_tip=summary_tip,
    )
