"""Redis-backed cache layer for market data providers.

Wraps any MarketDataProvider and caches quote/metadata responses in Redis.
All users share the same cache — ticker data is read-only and identical
across organizations, so a single cache entry serves every user who holds
the same symbol.

Cache keys
----------
quote:{symbol}              → QuoteData JSON          TTL = QUOTE_TTL (5 min)
metadata:{symbol}           → HoldingMetadata JSON    TTL = METADATA_TTL (24 h)
historical:{symbol}:{interval}:{start}:{end} → [HistoricalPrice] TTL = 7 days

Design constraints
------------------
* Never raise on cache miss or Redis failure — always fall through to provider.
* Batch fetches check cache per-symbol, fetch only missing, then merge.
* Manual refresh endpoints can bypass the cache by calling the provider directly.
"""

import asyncio
import json
import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.core import cache as redis_cache
from app.services.circuit_breaker import get_circuit_breaker

from .base_provider import (
    HistoricalPrice,
    HoldingMetadata,
    MarketDataProvider,
    QuoteData,
    SearchResult,
)

logger = logging.getLogger(__name__)

# TTLs in seconds — configurable via env vars in a future iteration
QUOTE_TTL = 300  # 5 minutes
METADATA_TTL = 86_400  # 24 hours
HISTORICAL_TTL = 604_800  # 7 days


class _DecimalEncoder(json.JSONEncoder):
    """Encode Decimal as str so Redis round-trips are lossless."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)


def _quote_key(symbol: str) -> str:
    return f"quote:{symbol.upper()}"


def _metadata_key(symbol: str) -> str:
    return f"metadata:{symbol.upper()}"


def _historical_key(symbol: str, interval: str, start: date, end: date) -> str:
    return f"historical:{symbol.upper()}:{interval}:{start.isoformat()}:{end.isoformat()}"


async def _cache_get_quote(symbol: str) -> Optional[QuoteData]:
    try:
        raw = await redis_cache.get(_quote_key(symbol))
        if raw is None:
            return None
        return QuoteData(**raw)
    except Exception:
        return None


async def _cache_set_quote(symbol: str, quote: QuoteData) -> None:
    try:
        data = json.loads(json.dumps(quote.model_dump(), cls=_DecimalEncoder))
        await redis_cache.setex(_quote_key(symbol), QUOTE_TTL, data)
    except Exception:
        pass


async def _cache_get_metadata(symbol: str) -> Optional[HoldingMetadata]:
    try:
        raw = await redis_cache.get(_metadata_key(symbol))
        if raw is None:
            return None
        return HoldingMetadata(**raw)
    except Exception:
        return None


async def _cache_set_metadata(symbol: str, meta: HoldingMetadata) -> None:
    try:
        data = json.loads(json.dumps(meta.model_dump(), cls=_DecimalEncoder))
        await redis_cache.setex(_metadata_key(symbol), METADATA_TTL, data)
    except Exception:
        pass


class CachedMarketDataProvider(MarketDataProvider):
    """Transparent caching wrapper around any MarketDataProvider."""

    def __init__(self, provider: MarketDataProvider):
        self._provider = provider
        self._cb = get_circuit_breaker()
        self._cb_service = provider.get_provider_name().lower().replace(" ", "_")

    # ------------------------------------------------------------------
    # Single quote
    # ------------------------------------------------------------------

    async def get_quote(self, symbol: str) -> QuoteData:
        cached = await _cache_get_quote(symbol)
        if cached is not None:
            logger.debug("quote cache HIT: %s", symbol)
            return cached

        logger.debug("quote cache MISS: %s", symbol)
        quote = await self._cb.call(
            self._cb_service, self._provider.get_quote, symbol
        )
        await _cache_set_quote(symbol, quote)
        return quote

    # ------------------------------------------------------------------
    # Batch quotes — check cache per symbol, fetch only missing
    # ------------------------------------------------------------------

    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, QuoteData]:
        result: Dict[str, QuoteData] = {}
        missing: List[str] = []

        # Parallel cache lookups instead of sequential awaits
        cached_results = await asyncio.gather(
            *[_cache_get_quote(sym) for sym in symbols]
        )
        for sym, cached in zip(symbols, cached_results):
            if cached is not None:
                result[sym] = cached
            else:
                missing.append(sym)

        if result:
            logger.info(
                "quote batch: %d cached, %d to fetch", len(result), len(missing)
            )

        if missing:
            fetched = await self._cb.call(
                self._cb_service, self._provider.get_quotes_batch, missing
            )
            # Parallel cache writes
            await asyncio.gather(
                *[_cache_set_quote(sym, quote) for sym, quote in fetched.items()]
            )
            result.update(fetched)

        return result

    # ------------------------------------------------------------------
    # Historical prices
    # ------------------------------------------------------------------

    async def get_historical_prices(
        self, symbol: str, start_date: date, end_date: date, interval: str = "1d"
    ) -> List[HistoricalPrice]:
        key = _historical_key(symbol, interval, start_date, end_date)
        raw = await redis_cache.get(key)
        if raw is not None:
            try:
                return [HistoricalPrice(**item) for item in raw]
            except Exception:
                pass

        prices = await self._cb.call(
            self._cb_service,
            self._provider.get_historical_prices,
            symbol, start_date, end_date, interval,
        )
        serialized = json.loads(
            json.dumps([p.model_dump() for p in prices], cls=_DecimalEncoder)
        )
        await redis_cache.setex(key, HISTORICAL_TTL, serialized)
        return prices

    # ------------------------------------------------------------------
    # Metadata (sector, industry, expense ratio) — rarely changes
    # ------------------------------------------------------------------

    async def get_holding_metadata(self, symbol: str) -> HoldingMetadata:
        cached = await _cache_get_metadata(symbol)
        if cached is not None:
            logger.debug("metadata cache HIT: %s", symbol)
            return cached

        meta = await self._cb.call(
            self._cb_service, self._provider.get_holding_metadata, symbol
        )
        await _cache_set_metadata(symbol, meta)
        return meta

    # ------------------------------------------------------------------
    # Pass-through (search is interactive, not worth caching)
    # ------------------------------------------------------------------

    async def search_symbol(self, query: str) -> List[SearchResult]:
        return await self._provider.search_symbol(query)

    def supports_realtime(self) -> bool:
        return self._provider.supports_realtime()

    def get_rate_limits(self) -> Dict[str, int]:
        return self._provider.get_rate_limits()

    def get_provider_name(self) -> str:
        return self._provider.get_provider_name()


# ------------------------------------------------------------------
# Public cache invalidation helpers (for refresh endpoints)
# ------------------------------------------------------------------


async def invalidate_quotes(*symbols: str) -> None:
    """Delete cached quotes for the given symbols so the next fetch hits the provider."""
    await asyncio.gather(
        *[redis_cache.delete(_quote_key(sym)) for sym in symbols]
    )
