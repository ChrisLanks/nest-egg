"""
CoinGecko market data provider.

FREE tier (no API key required):
- Crypto prices, market caps, 24h changes
- Historical OHLC data
- Search by name or symbol
- Rate limit: 10-30 calls/minute (no key), 500/min with free API key

Docs: https://docs.coingecko.com/reference/introduction
"""

import asyncio
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from time import time
from typing import Dict, List, Optional

import httpx

from .base_provider import (
    HistoricalPrice,
    HoldingMetadata,
    MarketDataProvider,
    QuoteData,
    SearchResult,
)
from .security import SymbolValidationError, validate_symbol

logger = logging.getLogger(__name__)

# Timeout for all external API calls (seconds)
REQUEST_TIMEOUT = 10.0

# Base URL for CoinGecko free API
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Well-known symbol-to-CoinGecko-ID mappings.
# Keys are uppercase Yahoo-style tickers (e.g. "BTC-USD").
# Values are CoinGecko coin IDs.
_SYMBOL_TO_ID: Dict[str, str] = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "BNB-USD": "binancecoin",
    "SOL-USD": "solana",
    "XRP-USD": "ripple",
    "ADA-USD": "cardano",
    "DOGE-USD": "dogecoin",
    "DOT-USD": "polkadot",
    "AVAX-USD": "avalanche-2",
    "MATIC-USD": "matic-network",
    "LINK-USD": "chainlink",
    "SHIB-USD": "shiba-inu",
    "LTC-USD": "litecoin",
    "UNI-USD": "uniswap",
    "ATOM-USD": "cosmos",
    "XLM-USD": "stellar",
    "ALGO-USD": "algorand",
    "FTM-USD": "fantom",
    "NEAR-USD": "near",
    "APE-USD": "apecoin",
    "AAVE-USD": "aave",
    "CRO-USD": "crypto-com-chain",
    "MANA-USD": "decentraland",
    "SAND-USD": "the-sandbox",
    "AXS-USD": "axie-infinity",
    "TRX-USD": "tron",
    "ETC-USD": "ethereum-classic",
    "FIL-USD": "filecoin",
    "ICP-USD": "internet-computer",
    "HBAR-USD": "hedera-hashgraph",
    "VET-USD": "vechain",
    "THETA-USD": "theta-token",
    "XTZ-USD": "tezos",
    "EOS-USD": "eos",
    "USDT-USD": "tether",
    "USDC-USD": "usd-coin",
    "DAI-USD": "dai",
    "BUSD-USD": "binance-usd",
    "ARB-USD": "arbitrum",
    "OP-USD": "optimism",
    "SUI-USD": "sui",
    "APT-USD": "aptos",
    "SEI-USD": "sei-network",
    "TIA-USD": "celestia",
    "PEPE-USD": "pepe",
}

# Reverse mapping: CoinGecko ID -> symbol
_ID_TO_SYMBOL: Dict[str, str] = {v: k for k, v in _SYMBOL_TO_ID.items()}


def _symbol_to_coingecko_id(symbol: str) -> str:
    """
    Convert a ticker symbol to a CoinGecko coin ID.

    Supports:
    - Direct mapping from _SYMBOL_TO_ID (e.g. "BTC-USD" -> "bitcoin")
    - Bare ticker with -USD suffix (e.g. "BTC" -> tries "BTC-USD")
    - Lowercase passthrough as last resort (e.g. "bitcoin" -> "bitcoin")
    """
    upper = symbol.upper()
    if upper in _SYMBOL_TO_ID:
        return _SYMBOL_TO_ID[upper]
    # Try appending -USD
    with_usd = f"{upper}-USD"
    if with_usd in _SYMBOL_TO_ID:
        return _SYMBOL_TO_ID[with_usd]
    # Fallback: assume the symbol itself is a CoinGecko ID
    return symbol.lower()


def _coingecko_id_to_symbol(cg_id: str) -> str:
    """Convert a CoinGecko ID back to a ticker symbol."""
    return _ID_TO_SYMBOL.get(cg_id, f"{cg_id.upper()}-USD")


class CoinGeckoProvider(MarketDataProvider):
    """CoinGecko implementation -- FREE, no API key required."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CoinGecko provider.

        Args:
            api_key: Optional CoinGecko API key for higher rate limits.
                     The free tier works without a key.
        """
        self.provider_name = "CoinGecko"
        self._api_key = api_key
        self._base_url = COINGECKO_BASE_URL
        # Reusable async client (created lazily)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx async client."""
        if self._client is None or self._client.is_closed:
            headers: Dict[str, str] = {
                "Accept": "application/json",
            }
            if self._api_key:
                headers["x-cg-demo-api-key"] = self._api_key
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=httpx.Timeout(REQUEST_TIMEOUT),
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        """
        Make an HTTP request to CoinGecko with retry on 429.

        Raises ValueError on non-retryable errors.
        """
        client = await self._get_client()
        max_retries = 2
        for attempt in range(max_retries + 1):
            resp = await client.request(method, path, **kwargs)
            if resp.status_code == 429:
                if attempt < max_retries:
                    retry_after = int(resp.headers.get("Retry-After", "5"))
                    wait = min(retry_after, 30)
                    logger.warning(
                        "coingecko_rate_limited",
                        extra={
                            "attempt": attempt + 1,
                            "retry_after": wait,
                        },
                    )
                    await asyncio.sleep(wait)
                    continue
                raise ValueError(
                    "CoinGecko rate limit exceeded. " "Try again later or add an API key."
                )
            resp.raise_for_status()
            return resp.json()
        # Should not be reached, but satisfy type checker
        raise ValueError("CoinGecko request failed")  # pragma: no cover

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    async def get_quote(self, symbol: str) -> QuoteData:
        """Get current quote from CoinGecko."""
        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError as e:
            logger.error(f"Symbol validation failed: {e}")
            raise ValueError(str(e))

        cg_id = _symbol_to_coingecko_id(symbol)

        logger.info(
            "external_api_call",
            extra={
                "provider": "coingecko",
                "operation": "get_quote",
                "symbol": symbol,
                "coingecko_id": cg_id,
            },
        )
        start_time = time()

        try:
            data = await self._request(
                "GET",
                "/simple/price",
                params={
                    "ids": cg_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                },
            )

            coin = data.get(cg_id)
            if not coin or "usd" not in coin:
                raise ValueError(f"No price data for {symbol} (id={cg_id})")

            price = Decimal(str(coin["usd"]))
            market_cap_raw = coin.get("usd_market_cap")
            change_pct_raw = coin.get("usd_24h_change")
            volume_raw = coin.get("usd_24h_vol")

            market_cap = Decimal(str(market_cap_raw)) if market_cap_raw is not None else None
            change_percent = Decimal(str(change_pct_raw)) if change_pct_raw is not None else None
            change = price * change_percent / Decimal("100") if change_percent is not None else None
            volume = int(float(volume_raw)) if volume_raw is not None else None

            quote = QuoteData(
                symbol=symbol.upper(),
                price=price,
                currency="USD",
                market_cap=market_cap,
                change=change,
                change_percent=change_percent,
                volume=volume,
            )

            duration_ms = (time() - start_time) * 1000
            logger.info(
                "external_api_success",
                extra={
                    "provider": "coingecko",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "price": float(quote.price),
                },
            )
            return quote

        except httpx.HTTPStatusError as e:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_failure",
                extra={
                    "provider": "coingecko",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "status": e.response.status_code,
                    "error": str(e),
                },
            )
            raise ValueError(f"CoinGecko API error for {symbol}: {e}")
        except httpx.TimeoutException:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_timeout",
                extra={
                    "provider": "coingecko",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "timeout_seconds": REQUEST_TIMEOUT,
                },
            )
            raise ValueError(
                f"Request timeout for {symbol} -- " "CoinGecko did not respond in time"
            )
        except ValueError:
            raise
        except Exception as e:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_failure",
                extra={
                    "provider": "coingecko",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to fetch quote for {symbol}: {e}")

    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """Get quotes for multiple symbols in a single API call."""
        logger.info(
            "external_api_call",
            extra={
                "provider": "coingecko",
                "operation": "get_quotes_batch",
                "symbol_count": len(symbols),
                "symbols": symbols[:10],
            },
        )
        start_time = time()

        # Build id list
        id_map: Dict[str, str] = {}  # cg_id -> original symbol
        for sym in symbols:
            try:
                validated = validate_symbol(sym)
            except SymbolValidationError:
                continue
            cg_id = _symbol_to_coingecko_id(validated)
            id_map[cg_id] = validated

        if not id_map:
            return {}

        try:
            data = await self._request(
                "GET",
                "/simple/price",
                params={
                    "ids": ",".join(id_map.keys()),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                },
            )
        except Exception as e:
            logger.error(f"Batch quote failed, falling back: {e}")
            # Fallback to individual fetches
            quotes: Dict[str, QuoteData] = {}
            for sym in symbols:
                try:
                    quotes[sym] = await self.get_quote(sym)
                except Exception:
                    pass
            return quotes

        quotes = {}
        for cg_id, sym in id_map.items():
            coin = data.get(cg_id)
            if not coin or "usd" not in coin:
                continue

            price = Decimal(str(coin["usd"]))
            mkt = coin.get("usd_market_cap")
            chg = coin.get("usd_24h_change")
            vol = coin.get("usd_24h_vol")

            market_cap = Decimal(str(mkt)) if mkt is not None else None
            change_pct = Decimal(str(chg)) if chg is not None else None
            change = price * change_pct / Decimal("100") if change_pct is not None else None
            volume = int(float(vol)) if vol is not None else None

            quotes[sym] = QuoteData(
                symbol=sym.upper(),
                price=price,
                currency="USD",
                market_cap=market_cap,
                change=change,
                change_percent=change_pct,
                volume=volume,
            )

        duration_ms = (time() - start_time) * 1000
        logger.info(
            "external_api_success",
            extra={
                "provider": "coingecko",
                "operation": "get_quotes_batch",
                "symbol_count": len(symbols),
                "successful_count": len(quotes),
                "duration_ms": duration_ms,
            },
        )
        return quotes

    async def get_historical_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: str = "1d",
    ) -> List[HistoricalPrice]:
        """Get historical price data from CoinGecko."""
        logger.info(
            "external_api_call",
            extra={
                "provider": "coingecko",
                "operation": "get_historical_prices",
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "interval": interval,
            },
        )
        start_time = time()

        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError as e:
            raise ValueError(str(e))

        cg_id = _symbol_to_coingecko_id(symbol)

        # CoinGecko uses days parameter; compute from date range
        days = (end_date - start_date).days
        if days <= 0:
            days = 1

        try:
            data = await self._request(
                "GET",
                f"/coins/{cg_id}/market_chart",
                params={
                    "vs_currency": "usd",
                    "days": str(days),
                },
            )

            raw_prices = data.get("prices", [])
            if not raw_prices:
                duration_ms = (time() - start_time) * 1000
                logger.warning(
                    "external_api_empty",
                    extra={
                        "provider": "coingecko",
                        "operation": "get_historical_prices",
                        "symbol": symbol,
                        "duration_ms": duration_ms,
                    },
                )
                return []

            # CoinGecko returns [[timestamp_ms, price], ...]
            # Group by date and build OHLCV-like data
            daily: Dict[date, List[Decimal]] = {}
            for ts_ms, px in raw_prices:
                dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).date()
                if start_date <= dt <= end_date:
                    daily.setdefault(dt, []).append(Decimal(str(px)))

            prices: List[HistoricalPrice] = []
            for dt in sorted(daily):
                pts = daily[dt]
                prices.append(
                    HistoricalPrice(
                        date=dt,
                        open=pts[0],
                        high=max(pts),
                        low=min(pts),
                        close=pts[-1],
                        volume=0,  # market_chart doesn't give vol per point
                    )
                )

            duration_ms = (time() - start_time) * 1000
            logger.info(
                "external_api_success",
                extra={
                    "provider": "coingecko",
                    "operation": "get_historical_prices",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "data_points": len(prices),
                },
            )
            return prices

        except httpx.TimeoutException:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_timeout",
                extra={
                    "provider": "coingecko",
                    "operation": "get_historical_prices",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "timeout_seconds": REQUEST_TIMEOUT,
                },
            )
            raise ValueError(
                f"Request timeout for {symbol} -- " "CoinGecko did not respond in time"
            )
        except ValueError:
            raise
        except Exception as e:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_failure",
                extra={
                    "provider": "coingecko",
                    "operation": "get_historical_prices",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to fetch historical data " f"for {symbol}: {e}")

    async def search_symbol(self, query: str) -> List[SearchResult]:
        """Search for crypto coins by name or symbol."""
        logger.info(
            "external_api_call",
            extra={
                "provider": "coingecko",
                "operation": "search_symbol",
                "query": query,
            },
        )
        start_time = time()

        try:
            data = await self._request(
                "GET",
                "/search",
                params={"query": query},
            )

            results: List[SearchResult] = []
            for coin in data.get("coins", [])[:20]:
                cg_id = coin.get("id", "")
                sym = _coingecko_id_to_symbol(cg_id)
                results.append(
                    SearchResult(
                        symbol=sym,
                        name=coin.get("name", cg_id),
                        type="crypto",
                        exchange="CoinGecko",
                        currency="USD",
                    )
                )

            duration_ms = (time() - start_time) * 1000
            logger.info(
                "external_api_success",
                extra={
                    "provider": "coingecko",
                    "operation": "search_symbol",
                    "query": query,
                    "duration_ms": duration_ms,
                    "result_count": len(results),
                },
            )
            return results

        except Exception as e:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_failure",
                extra={
                    "provider": "coingecko",
                    "operation": "search_symbol",
                    "query": query,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
            )
            return []

    async def get_holding_metadata(self, symbol: str) -> HoldingMetadata:
        """
        Fetch classification metadata for a crypto holding.

        Uses /coins/{id} for full metadata including category
        and description.
        """
        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError as e:
            logger.warning(f"Symbol validation failed for metadata: {e}")
            return HoldingMetadata(symbol=symbol)

        cg_id = _symbol_to_coingecko_id(symbol)

        try:
            data = await self._request(
                "GET",
                f"/coins/{cg_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                },
            )
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {symbol}: {e}")
            return HoldingMetadata(symbol=symbol)

        name = data.get("name")
        categories = data.get("categories", [])
        sector = categories[0] if categories else None

        # Market cap classification
        market_data = data.get("market_data", {})
        mkt_cap_usd = market_data.get("market_cap", {}).get("usd")
        if mkt_cap_usd is not None:
            if mkt_cap_usd >= 10_000_000_000:
                market_cap = "large"
            elif mkt_cap_usd >= 2_000_000_000:
                market_cap = "mid"
            else:
                market_cap = "small"
        else:
            market_cap = None

        # Country of origin from genesis/hq is not reliable
        # for crypto; leave as None.
        return HoldingMetadata(
            symbol=symbol.upper(),
            name=name,
            asset_type="crypto",
            asset_class=None,
            market_cap=market_cap,
            sector=sector,
            industry=None,
            country=None,
        )

    def supports_realtime(self) -> bool:
        """CoinGecko free tier has ~60s delay."""
        return False

    def get_rate_limits(self) -> Dict[str, int]:
        """CoinGecko rate limits depend on tier."""
        if self._api_key:
            return {
                "calls_per_minute": 500,
                "calls_per_day": 0,
                "note": "Free API key tier",
            }
        return {
            "calls_per_minute": 10,
            "calls_per_day": 0,
            "note": ("Free tier without API key " "(10-30 calls/min)"),
        }

    def get_provider_name(self) -> str:
        """Get provider name."""
        return self.provider_name

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
