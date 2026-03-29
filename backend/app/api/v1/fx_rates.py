"""FX Rates API endpoint — wraps fx_service for frontend consumption."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.user import User
from app.services.fx_service import get_rates_with_meta, supported_currencies, SUPPORTED_CURRENCIES

router = APIRouter()


class FXRateResponse(BaseModel):
    base: str
    rates: dict
    supported_currencies: List[str]
    is_fallback: bool = False
    data_note: str = ""


@router.get("/fx-rates", response_model=FXRateResponse)
async def get_fx_rates(
    currencies: Optional[str] = Query(None, description="Comma-separated currency codes, e.g. EUR,GBP,JPY"),
    current_user: User = Depends(get_current_user),
):
    """
    Return exchange rates for requested currencies (base USD).

    `is_fallback=true` and `data_note` are set when the live Frankfurter/ECB
    API is unreachable and approximate static rates are used instead. The UI
    should display a warning in that case.
    """
    result = await get_rates_with_meta("USD")

    if currencies:
        requested = {c.strip().upper() for c in currencies.split(",")}
        rates = {k: v for k, v in result.rates.items() if k in requested}
    else:
        rates = {k: v for k, v in result.rates.items() if k != "USD"}

    return FXRateResponse(
        base="USD",
        rates=rates,
        supported_currencies=supported_currencies(),
        is_fallback=result.is_fallback,
        data_note=result.data_note,
    )
