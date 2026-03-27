"""Dynamic IRS/SSA limits fetcher with Redis caching and static fallback.

Attempts to fetch authoritative government data for tax limits.  Falls back
gracefully to static constants from ``financial.py`` when network or Redis
is unavailable.  Never blocks startup — all fetches are lazy.

Cache strategy
--------------
- Redis key pattern: ``irs_limits:{year}:{category}``
- TTL: 7 days (604 800 seconds)
- On cache miss → attempt live fetch → on failure → static fallback

Usage::

    from app.services.irs_limits_fetcher import get_limits_data

    data = await get_limits_data(2026, "retirement")
    # data.source in ("live", "cached", "static_2026")
"""

from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CACHE_TTL = 604_800  # 7 days in seconds


@dataclass
class LimitsData:
    """Wrapper around fetched/cached/static limit values."""

    value: Any
    source: str  # "live", "cached", "static_YYYY"
    as_of: str  # ISO date string
    note: Optional[str] = None
    cache_expires: Optional[str] = None


# ── Redis helpers ────────────────────────────────────────────────────────

_redis_client = None


async def _get_redis():
    """Return a shared Redis client, or None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        from app.config import settings

        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        await client.ping()
        _redis_client = client
        return client
    except Exception as exc:
        logger.debug("irs_limits_fetcher: Redis unavailable: %s", exc)
        return None


async def _cache_get(key: str) -> Optional[str]:
    """Read from Redis cache; return None on miss or error."""
    r = await _get_redis()
    if r is None:
        return None
    try:
        return await r.get(key)
    except Exception:
        return None


async def _cache_set(key: str, value: str, ttl: int = _CACHE_TTL) -> None:
    """Write to Redis cache; silently ignore errors."""
    r = await _get_redis()
    if r is None:
        return
    try:
        await r.setex(key, ttl, value)
    except Exception:
        pass


# ── Live fetch strategies ────────────────────────────────────────────────


async def _try_ssa_wage_base(year: int) -> Optional[dict]:
    """Social Security wage base lookup.

    NOTE: This function returns None to defer to the static fallback in
    ``financial.py``, which contains IRS/SSA-confirmed values updated each
    November.  The prior implementation hit SSA's website but did not
    actually parse the wage base from the HTML — it only checked whether
    the year appeared on the page.  Rather than maintain a fragile
    scraper, we rely on the well-maintained ``_SS_DATA`` table in
    ``financial.py`` and surface clear ``DataSourceMeta`` indicating
    the data is static.

    Last manual verification: 2025-11-15 against ssa.gov/oact/cola/cbb.html
    """
    # Always return None so the caller falls through to the static fallback
    # which is accurate and annually updated in financial.py.
    return None


async def _try_irs_api(year: int, category: str) -> Optional[dict]:
    """Attempt to hit the IRS API (does not exist as of 2026)."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"https://api.irs.gov/limits/{year}/{category}"
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


# ── Static fallback ──────────────────────────────────────────────────────


def _static_fallback(year: int, category: str) -> dict:
    """Return static data from financial.py for the given year/category."""
    from app.constants.financial import (
        MEDICARE,
        RETIREMENT,
        SS,
        TAX,
    )

    resolvers = {
        "retirement": RETIREMENT.for_year,
        "tax": TAX.for_year,
        "ss": SS.for_year,
        "medicare": MEDICARE.for_year,
    }
    resolver = resolvers.get(category)
    if resolver:
        return resolver(year)
    return {}


# ── Public API ───────────────────────────────────────────────────────────


async def get_limits_data(year: int, category: str) -> LimitsData:
    """Fetch IRS/SSA limits for *year* and *category*.

    Tries (in order): Redis cache → live fetch → static fallback.
    Never raises — always returns a ``LimitsData`` with appropriate
    ``source`` metadata.

    Parameters
    ----------
    year : int
        Tax year (e.g. 2026).
    category : str
        One of: "retirement", "tax", "ss", "medicare".
    """
    today = datetime.date.today().isoformat()
    cache_key = f"irs_limits:{year}:{category}"

    # 1. Try Redis cache
    cached = await _cache_get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            return LimitsData(
                value=data.get("value", data),
                source="cached",
                as_of=data.get("as_of", today),
                note="Served from Redis cache",
                cache_expires=data.get("cache_expires"),
            )
        except (json.JSONDecodeError, KeyError):
            pass

    # 2. Try live fetch (best-effort)
    live_data = None
    if category == "ss":
        live_data = await _try_ssa_wage_base(year)
    else:
        live_data = await _try_irs_api(year, category)

    if live_data is not None:
        # Cache the live result
        expires = datetime.date.today() + datetime.timedelta(days=7)
        payload = {
            "value": live_data,
            "as_of": today,
            "cache_expires": expires.isoformat(),
        }
        await _cache_set(cache_key, json.dumps(payload))
        return LimitsData(
            value=live_data,
            source="live",
            as_of=today,
            note="Fetched from government source",
            cache_expires=expires.isoformat(),
        )

    # 3. Static fallback (authoritative — updated each November from IRS/SSA publications)
    static = _static_fallback(year, category)
    return LimitsData(
        value=static,
        source=f"static_{year}",
        as_of=today,
        note=(
            f"Static IRS/SSA {year} limits from financial.py "
            "(last verified 2025-11-15). Updated annually when IRS publishes new values."
        ),
    )


def make_data_source_meta(limits_data: LimitsData) -> dict:
    """Convert LimitsData to a dict matching the DataSourceMeta schema."""
    return {
        "source": limits_data.source,
        "as_of": limits_data.as_of,
        "note": limits_data.note,
        "cache_expires": limits_data.cache_expires,
    }
