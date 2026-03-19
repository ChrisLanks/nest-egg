"""
Mortgage Rate Watch — fetches current 30-yr and 15-yr fixed mortgage rates
from the FRED public CSV API (St. Louis Federal Reserve, no API key needed).

Series:
  MORTGAGE30US — 30-year fixed rate mortgage average (weekly, Freddie Mac)
  MORTGAGE15US — 15-year fixed rate mortgage average (weekly, Freddie Mac)

Falls back gracefully when FRED is unreachable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Tuple

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_30YR_URL = f"{FRED_CSV_BASE}?id=MORTGAGE30US"
FRED_15YR_URL = f"{FRED_CSV_BASE}?id=MORTGAGE15US"
_TIMEOUT = 8.0


class MortgageRateSnapshot(BaseModel):
    rate_30yr: Optional[float]  # decimal, e.g. 0.0675 for 6.75%
    rate_15yr: Optional[float]
    as_of_date: Optional[str]  # "YYYY-MM-DD"
    source: str = "FRED / Freddie Mac"


async def _fetch_latest_fred_rate(url: str) -> Tuple[Optional[float], Optional[str]]:
    """Fetch the most recent non-null rate from a FRED public CSV series."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        # CSV: DATE,VALUE header on line 0; walk backwards for most-recent valid value
        for line in reversed(lines[1:]):
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() not in (".", ""):
                try:
                    rate_pct = float(parts[1].strip())
                    return round(rate_pct / 100, 6), parts[0].strip()
                except ValueError:
                    continue
    except Exception as exc:
        logger.warning("FRED fetch failed (%s): %s", url, exc)
    return None, None


async def get_current_mortgage_rates() -> MortgageRateSnapshot:
    """
    Return latest 30-yr and 15-yr fixed rates from FRED, fetched concurrently.
    Returns None for each rate on failure so the caller handles gracefully.
    """
    (rate_30, date_30), (rate_15, _) = await asyncio.gather(
        _fetch_latest_fred_rate(FRED_30YR_URL),
        _fetch_latest_fred_rate(FRED_15YR_URL),
    )
    return MortgageRateSnapshot(
        rate_30yr=rate_30,
        rate_15yr=rate_15,
        as_of_date=date_30,
    )
