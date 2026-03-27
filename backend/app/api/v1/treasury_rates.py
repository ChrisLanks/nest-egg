"""Treasury yield curve API endpoint — fetches current rates from FRED."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.cache import get as cache_get
from app.core.cache import setex as cache_setex
from app.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_TIMEOUT = 8.0
_CACHE_TTL = 86400  # 24 hours

# FRED series IDs for the Treasury yield curve
TREASURY_SERIES = {
    "1_month": "DGS1MO",
    "3_month": "DGS3MO",
    "6_month": "DGS6MO",
    "1_year": "DGS1",
    "2_year": "DGS2",
    "5_year": "DGS5",
    "10_year": "DGS10",
    "30_year": "DGS30",
}


class TreasuryRateResponse(BaseModel):
    rates: Dict[str, Optional[float]]
    as_of_date: Optional[str] = None
    source: str = "FRED / U.S. Treasury"


async def _fetch_fred_rate(series_id: str) -> tuple[Optional[float], Optional[str]]:
    """Fetch the most recent non-null rate from a FRED CSV series."""
    url = f"{FRED_CSV_BASE}?id={series_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        for line in reversed(lines[1:]):
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() not in (".", ""):
                try:
                    rate_pct = float(parts[1].strip())
                    return round(rate_pct / 100, 6), parts[0].strip()
                except ValueError:
                    continue
    except Exception as exc:
        logger.warning("FRED treasury fetch failed (%s): %s", series_id, exc)
    return None, None


@router.get("/treasury-rates", response_model=TreasuryRateResponse)
async def get_treasury_rates(
    current_user: User = Depends(get_current_user),
):
    """Return current Treasury yield curve from FRED (cached 24h)."""
    cache_key = "market_data:treasury_rates"
    cached = await cache_get(cache_key)
    if cached is not None:
        return TreasuryRateResponse(**cached)

    tasks = {label: _fetch_fred_rate(series_id) for label, series_id in TREASURY_SERIES.items()}
    results = await asyncio.gather(*tasks.values())

    rates = {}
    latest_date = None
    for label, (rate, as_of) in zip(tasks.keys(), results):
        rates[label] = rate
        if as_of and (latest_date is None or as_of > latest_date):
            latest_date = as_of

    data = {"rates": rates, "as_of_date": latest_date, "source": "FRED / U.S. Treasury"}
    await cache_setex(cache_key, _CACHE_TTL, data)

    return TreasuryRateResponse(**data)
