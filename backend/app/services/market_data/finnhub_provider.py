"""
Finnhub market data provider.

Free tier: 60 API calls/minute.
- Real-time quotes (15-min delay on free)
- Company profiles, financials, earnings
- Symbol search
- Stock candles (historical data)

Requires: FINNHUB_API_KEY environment variable.
"""

import asyncio
import logging
from datetime import date
from decimal import Decimal
from time import time
from typing import Dict, List

import finnhub

from app.config import settings

from .base_provider import (
    HoldingMetadata,
    HistoricalPrice,
    MarketDataProvider,
    QuoteData,
    SearchResult,
)
from .security import SymbolValidationError, validate_symbol

logger = logging.getLogger(__name__)

# Timeout for all external API calls (seconds)
REQUEST_TIMEOUT = 10.0


class FinnhubProvider(MarketDataProvider):
    """Finnhub implementation — 60 free calls/min."""

    def __init__(self):
        api_key = settings.FINNHUB_API_KEY
        if not api_key:
            raise ValueError(
                "FINNHUB_API_KEY is not configured. "
                "Get a free key at https://finnhub.io/"
            )
        self._client = finnhub.Client(api_key=api_key)

    async def get_quote(self, symbol: str) -> QuoteData:
        """Get current quote from Finnhub."""
        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError as e:
            raise ValueError(str(e))

        logger.info(
            "external_api_call",
            extra={"provider": "finnhub", "operation": "get_quote", "symbol": symbol},
        )
        start_time = time()

        try:
            # Finnhub quote returns: c(current), h(high), l(low), o(open),
            # pc(previous close), d(change), dp(change percent), t(timestamp)
            quote = await asyncio.wait_for(
                asyncio.to_thread(self._client.quote, symbol),
                timeout=REQUEST_TIMEOUT,
            )

            if not quote or quote.get("c") is None or quote["c"] == 0:
                raise ValueError(f"No price data available for {symbol}")

            # Fetch company profile for name, exchange, market cap
            profile = {}
            try:
                profile = await asyncio.wait_for(
                    asyncio.to_thread(self._client.company_profile2, symbol=symbol),
                    timeout=REQUEST_TIMEOUT,
                )
            except Exception:
                pass  # Profile is optional enrichment

            duration_ms = (time() - start_time) * 1000
            logger.info(
                "external_api_success",
                extra={
                    "provider": "finnhub",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "price": quote["c"],
                },
            )

            return QuoteData(
                symbol=symbol.upper(),
                price=Decimal(str(quote["c"])),
                name=profile.get("name"),
                currency=profile.get("currency", "USD"),
                exchange=profile.get("exchange"),
                market_cap=Decimal(str(profile["marketCapitalization"] * 1_000_000))
                if profile.get("marketCapitalization")
                else None,
                change=Decimal(str(quote["d"])) if quote.get("d") is not None else None,
                change_percent=Decimal(str(quote["dp"]))
                if quote.get("dp") is not None
                else None,
                previous_close=Decimal(str(quote["pc"]))
                if quote.get("pc")
                else None,
                open=Decimal(str(quote["o"])) if quote.get("o") else None,
                high=Decimal(str(quote["h"])) if quote.get("h") else None,
                low=Decimal(str(quote["l"])) if quote.get("l") else None,
            )

        except asyncio.TimeoutError:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_timeout",
                extra={
                    "provider": "finnhub",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                },
            )
            raise ValueError(f"Request timeout for {symbol}")
        except ValueError:
            raise
        except Exception as e:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_failure",
                extra={
                    "provider": "finnhub",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to fetch quote for {symbol}: {e}")

    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """Get multiple quotes (sequential — Finnhub has no batch endpoint)."""
        logger.info(
            "external_api_call",
            extra={
                "provider": "finnhub",
                "operation": "get_quotes_batch",
                "symbol_count": len(symbols),
            },
        )
        quotes: Dict[str, QuoteData] = {}
        for symbol in symbols:
            try:
                quotes[symbol] = await self.get_quote(symbol)
            except Exception as e:
                logger.warning(f"Failed to fetch quote for {symbol}: {e}")
        return quotes

    async def get_historical_prices(
        self, symbol: str, start_date: date, end_date: date, interval: str = "1d"
    ) -> List[HistoricalPrice]:
        """Get historical price data via stock candles."""
        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError as e:
            raise ValueError(str(e))

        # Map interval to Finnhub resolution
        resolution_map = {"1d": "D", "1wk": "W", "1mo": "M"}
        resolution = resolution_map.get(interval, "D")

        import calendar
        from datetime import datetime

        from_ts = int(
            calendar.timegm(datetime(start_date.year, start_date.month, start_date.day).timetuple())
        )
        to_ts = int(
            calendar.timegm(datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59).timetuple())
        )

        logger.info(
            "external_api_call",
            extra={
                "provider": "finnhub",
                "operation": "get_historical_prices",
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        start_time = time()

        try:
            candles = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.stock_candles, symbol, resolution, from_ts, to_ts
                ),
                timeout=REQUEST_TIMEOUT * 2,
            )

            if not candles or candles.get("s") != "ok":
                raise ValueError(f"No historical data for {symbol}")

            prices = []
            for i in range(len(candles["t"])):
                dt = datetime.utcfromtimestamp(candles["t"][i]).date()
                prices.append(
                    HistoricalPrice(
                        date=dt,
                        open=Decimal(str(candles["o"][i])),
                        high=Decimal(str(candles["h"][i])),
                        low=Decimal(str(candles["l"][i])),
                        close=Decimal(str(candles["c"][i])),
                        volume=int(candles["v"][i]),
                        adjusted_close=Decimal(str(candles["c"][i])),
                    )
                )

            duration_ms = (time() - start_time) * 1000
            logger.info(
                "external_api_success",
                extra={
                    "provider": "finnhub",
                    "operation": "get_historical_prices",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "data_points": len(prices),
                },
            )
            return prices

        except asyncio.TimeoutError:
            raise ValueError(f"Request timeout for {symbol} historical data")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to fetch historical data for {symbol}: {e}")

    async def search_symbol(self, query: str) -> List[SearchResult]:
        """Search for symbols using Finnhub symbol lookup."""
        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(self._client.symbol_lookup, query),
                timeout=REQUEST_TIMEOUT,
            )

            if not results or "result" not in results:
                return []

            search_results = []
            for item in results["result"][:20]:  # Limit to 20 results
                # Map Finnhub type to our type
                finnhub_type = (item.get("type") or "").upper()
                type_map = {
                    "COMMON STOCK": "stock",
                    "ETP": "etf",
                    "ETF": "etf",
                    "REIT": "stock",
                    "MUTUAL FUND": "mutual_fund",
                    "CRYPTO": "crypto",
                }
                security_type = type_map.get(finnhub_type, "stock")

                search_results.append(
                    SearchResult(
                        symbol=item.get("symbol", ""),
                        name=item.get("description", query),
                        type=security_type,
                        exchange=item.get("displaySymbol"),
                    )
                )
            return search_results

        except Exception as e:
            logger.warning(f"Finnhub symbol search failed for {query}: {e}")
            return []

    async def get_holding_metadata(self, symbol: str) -> HoldingMetadata:
        """Get classification metadata from Finnhub company profile."""
        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError:
            return HoldingMetadata(symbol=symbol)

        try:
            profile = await asyncio.wait_for(
                asyncio.to_thread(self._client.company_profile2, symbol=symbol),
                timeout=REQUEST_TIMEOUT,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {symbol}: {e}")
            return HoldingMetadata(symbol=symbol)

        if not profile:
            return HoldingMetadata(symbol=symbol)

        # Market cap classification
        market_cap_value = profile.get("marketCapitalization", 0) * 1_000_000  # Finnhub reports in millions
        if market_cap_value >= 10_000_000_000:
            market_cap = "large"
        elif market_cap_value >= 2_000_000_000:
            market_cap = "mid"
        elif market_cap_value > 0:
            market_cap = "small"
        else:
            market_cap = None

        country = profile.get("country")
        asset_class = "domestic" if country == "US" else "international" if country else None

        return HoldingMetadata(
            symbol=symbol,
            name=profile.get("name"),
            asset_type="stock",  # Finnhub profiles are for stocks
            asset_class=asset_class,
            market_cap=market_cap,
            sector=profile.get("finnhubIndustry"),
            industry=profile.get("finnhubIndustry"),
            country=country,
        )

    def supports_realtime(self) -> bool:
        """Finnhub free tier has 15-min delay."""
        return True

    def get_rate_limits(self) -> Dict[str, int]:
        return {"calls_per_minute": 60}

    def get_provider_name(self) -> str:
        return "Finnhub"
