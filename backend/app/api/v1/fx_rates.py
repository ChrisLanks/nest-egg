"""FX Rates API endpoint — wraps fx_service for frontend consumption."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.user import User
from app.services.fx_service import get_rate, supported_currencies, SUPPORTED_CURRENCIES

router = APIRouter()


class FXRateResponse(BaseModel):
    base: str
    rates: dict
    supported_currencies: List[str]


@router.get("/fx-rates", response_model=FXRateResponse)
async def get_fx_rates(
    currencies: Optional[str] = Query(None, description="Comma-separated currency codes, e.g. EUR,GBP,JPY"),
    current_user: User = Depends(get_current_user),
):
    """Return exchange rates for requested currencies (base USD)."""
    if currencies:
        requested = [c.strip().upper() for c in currencies.split(",")]
    else:
        requested = [c for c in SUPPORTED_CURRENCIES if c != "USD"]

    rates = {}
    for currency in requested:
        rate = await get_rate("USD", currency)
        rates[currency] = rate

    return FXRateResponse(
        base="USD",
        rates=rates,
        supported_currencies=supported_currencies(),
    )
