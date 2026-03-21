"""TaxGraphs provider: fetches bracket data from the taxgraphs GitHub repo.

Data source: https://github.com/hermantran/taxgraphs (CC BY-NC 4.0)
URL pattern: https://raw.githubusercontent.com/hermantran/taxgraphs/master/data/{year}/taxes.json

Fallback chain:
  1. Redis cache (TTL 24 hours)
  2. Live HTTP fetch from taxgraphs repo
  3. Static bundled rates dict (StaticStateTaxProvider)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

from app.constants.state_tax_rates import STATE_TAX_RATES
from app.services.tax_rate_providers.base import StateTaxBracket, StateTaxProvider

logger = logging.getLogger(__name__)

_TAXGRAPHS_URL = (
    "https://raw.githubusercontent.com/hermantran/taxgraphs/master/data/{year}/taxes.json"
)
_CACHE_TTL = 86400  # 24 hours
_CACHE_KEY_PREFIX = "state_tax_rates"

# Map our internal filing statuses to taxgraphs keys
_FILING_STATUS_MAP = {
    "single": "single",
    "married": "married",
    "married_jointly": "married",
    "married_filing_jointly": "married",
}


def _parse_brackets(raw_brackets: list[list]) -> list[StateTaxBracket]:
    """Convert taxgraphs bracket list [[floor, rate, cumtax], ...] to StateTaxBracket objects."""
    result: list[StateTaxBracket] = []
    for i, entry in enumerate(raw_brackets):
        floor = float(entry[0])
        rate = float(entry[1])
        # ceiling is next bracket's floor, or infinity for the last bracket
        if i + 1 < len(raw_brackets):
            ceiling = float(raw_brackets[i + 1][0])
        else:
            ceiling = float("inf")
        result.append(StateTaxBracket(min_income=floor, max_income=ceiling, rate=rate))
    return result


def _find_rate_in_brackets(brackets: list[StateTaxBracket], income: float) -> float:
    """Return the marginal rate for the bracket containing income."""
    for bracket in reversed(brackets):
        if income >= bracket.min_income:
            return bracket.rate
    # income is below all brackets (e.g. 0 income)
    return brackets[0].rate if brackets else 0.0


class TaxGraphsProvider(StateTaxProvider):
    """
    Fetches state income tax brackets from the taxgraphs GitHub repo.

    Falls back to the static bundled rates if the network or Redis is unavailable.
    """

    def __init__(self) -> None:
        self._redis_client: Any = None
        self._redis_available: Optional[bool] = None  # None = not yet tested
        self._static_fallback = None  # lazy import to avoid circular

    def source_name(self) -> str:
        return "taxgraphs_github"

    def tax_year(self) -> int:
        return datetime.now().year

    # ── Redis helpers ───────────────────────────────────────────────────────

    async def _get_redis(self) -> Any:
        """Return a Redis client, or None if Redis is unavailable."""
        if self._redis_available is False:
            return None
        if self._redis_client is not None:
            return self._redis_client
        try:
            import redis.asyncio as redis_asyncio

            from app.config import settings

            redis_url = settings.REDIS_URL
            self._redis_client = redis_asyncio.from_url(
                redis_url, encoding="utf-8", decode_responses=True
            )
            # Ping to verify the connection is alive
            await self._redis_client.ping()
            self._redis_available = True
            return self._redis_client
        except Exception as exc:
            logger.warning("TaxGraphsProvider: Redis unavailable (%s), skipping cache.", exc)
            self._redis_available = False
            self._redis_client = None
            return None

    async def _cache_get(self, year: int) -> Optional[dict]:
        """Fetch cached taxgraphs data for year, or None on miss/error."""
        client = await self._get_redis()
        if client is None:
            return None
        try:
            raw = await client.get(f"{_CACHE_KEY_PREFIX}:{year}")
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("TaxGraphsProvider: cache read error (%s).", exc)
        return None

    async def _cache_set(self, year: int, data: dict) -> None:
        """Store taxgraphs data in Redis with TTL."""
        client = await self._get_redis()
        if client is None:
            return
        try:
            await client.setex(f"{_CACHE_KEY_PREFIX}:{year}", _CACHE_TTL, json.dumps(data))
        except Exception as exc:
            logger.warning("TaxGraphsProvider: cache write error (%s).", exc)

    # ── HTTP fetch ──────────────────────────────────────────────────────────

    async def _fetch_taxgraphs(self, year: int) -> Optional[dict]:
        """
        Fetch taxgraphs JSON for year.  Returns None on any error (404, network, etc.).
        """
        url = _TAXGRAPHS_URL.format(year=year)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
                if response.status_code == 404:
                    return None
                logger.warning(
                    "TaxGraphsProvider: unexpected HTTP %s for year %s.",
                    response.status_code,
                    year,
                )
                return None
        except Exception as exc:
            logger.warning("TaxGraphsProvider: HTTP fetch failed for year %s: %s.", year, exc)
            return None

    # ── Data loading ────────────────────────────────────────────────────────

    async def _load_data(self) -> Optional[dict]:
        """
        Load taxgraphs data with fallback year logic:
          1. Try Redis cache for current year
          2. Try HTTP for current year
          3. Try Redis cache for current year - 1
          4. Try HTTP for current year - 1
          5. Return None (caller will use static fallback)
        """
        current_year = datetime.now().year

        for year in (current_year, current_year - 1):
            # Cache first
            cached = await self._cache_get(year)
            if cached is not None:
                return cached

            # Live fetch
            data = await self._fetch_taxgraphs(year)
            if data is not None:
                await self._cache_set(year, data)
                return data

        return None

    def _get_static_fallback(self):
        """Lazy-load the static fallback provider."""
        if self._static_fallback is None:
            from app.services.tax_rate_providers.static_provider import StaticStateTaxProvider

            self._static_fallback = StaticStateTaxProvider()
        return self._static_fallback

    # ── StateTaxProvider interface ──────────────────────────────────────────

    async def get_brackets(self, state: str, filing_status: str) -> list[StateTaxBracket]:
        """Return bracket list for state/filing_status from taxgraphs data."""
        data = await self._load_data()
        if data is None:
            logger.info(
                "TaxGraphsProvider: falling back to static for brackets (%s %s).",
                state,
                filing_status,
            )
            return await self._get_static_fallback().get_brackets(state, filing_status)

        state_upper = state.upper()
        tg_status = _FILING_STATUS_MAP.get(filing_status, "single")

        state_data = data.get(state_upper)
        if state_data is None:
            # State not in taxgraphs — may be no-income-tax or DC/territory
            fallback_rate = STATE_TAX_RATES.get(state_upper, 0.0)
            return [StateTaxBracket(min_income=0, max_income=float("inf"), rate=fallback_rate)]

        income_data = state_data.get("income", {})
        status_data = income_data.get(tg_status, {})
        raw_brackets = status_data.get("brackets")

        if not raw_brackets:
            # State has no income tax or data missing; treat as 0
            return [StateTaxBracket(min_income=0, max_income=float("inf"), rate=0.0)]

        return _parse_brackets(raw_brackets)

    async def get_rate(self, state: str, filing_status: str, income: float) -> float:
        """Return the marginal rate for the bracket containing income."""
        brackets = await self.get_brackets(state, filing_status)
        if not brackets:
            return 0.0
        return _find_rate_in_brackets(brackets, income)
