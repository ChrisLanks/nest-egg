"""ESPP (Employee Stock Purchase Plan) API endpoints."""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.services.rate_limit_service import rate_limit_service
from app.models.user import User
from app.services.espp_service import espp_service



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(dependencies=[Depends(_rate_limit)])


class ESPPAnalysisRequest(BaseModel):
    purchase_price: Decimal
    fmv_at_purchase: Decimal
    fmv_at_sale: Decimal
    shares: Decimal
    is_qualifying: bool = False  # True if qualifying disposition


class ESPPAnalysisResponse(BaseModel):
    ordinary_income: float
    capital_gain: float
    total_gain: float
    is_qualifying: bool
    max_discount_rate: float
    annual_purchase_limit: int


@router.post("/analysis", response_model=ESPPAnalysisResponse)
async def analyze_espp_disposition(
    body: ESPPAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze tax implications of an ESPP share disposition."""
    if body.is_qualifying:
        # Qualifying: ordinary income = lesser of (actual gain, discount at offering)
        discount = body.fmv_at_purchase - body.purchase_price
        actual_gain_per_share = body.fmv_at_sale - body.purchase_price
        ordinary_per_share = min(discount, max(actual_gain_per_share, Decimal("0")))
        ordinary_income = float(ordinary_per_share * body.shares)
        total_gain = float(espp_service.calculate_qualifying_gain(
            body.purchase_price, body.fmv_at_sale, body.shares
        ))
        capital_gain = total_gain - ordinary_income
    else:
        # Disqualifying: ordinary income = FMV at purchase - purchase price
        ordinary_income = float(espp_service.calculate_ordinary_income(
            body.purchase_price, body.fmv_at_purchase, body.shares
        ))
        capital_gain = float(espp_service.calculate_disqualifying_gain(
            body.fmv_at_purchase, body.fmv_at_sale, body.shares
        ))
        total_gain = ordinary_income + capital_gain

    return ESPPAnalysisResponse(
        ordinary_income=ordinary_income,
        capital_gain=capital_gain,
        total_gain=total_gain,
        is_qualifying=body.is_qualifying,
        max_discount_rate=float(espp_service.MAX_DISCOUNT_RATE),
        annual_purchase_limit=espp_service.ANNUAL_PURCHASE_LIMIT,
    )
