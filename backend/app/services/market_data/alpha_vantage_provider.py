"""
Alpha Vantage market data provider.

Free tier: 25 API calls/day, 5 calls/minute.
- Daily/weekly/monthly OHLCV
- Global quote (current price)
- Symbol search
- 60+ technical indicators (on paid tier)

Requires: ALPHA_VANTAGE_API_KEY environment variable.
"""

import asyncio
import logging
from datetime import date
from decimal import Decimal
from time import time
from typing import Dict, List

from alpha_vantage.timeseries import TimeSeries

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

REQUEST_TIMEOUT = 10.0


class AlphaVantageProvider(MarketDataProvider):
    """Alpha Vantage implementation — 25 free calls/day."""

    def __init__(self):
        api_key = settings.ALPHA_VANTAGE_API_KEY
        if not api_key:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY is not configured. "
                "Get a free key at https://www.alphavantage.co/support/#api-key"
            )
        self._api_key = api_key
        self._ts = TimeSeries(key=api_key, output_format="json")

    async def get_quote(self, symbol: str) -> QuoteData:
        """Get current quote from Alpha Vantage Global Quote endpoint."""
        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError as e:
            raise ValueError(str(e))

        logger.info(
            "external_api_call",
            extra={
                "provider": "alpha_vantage",
                "operation": "get_quote",
                "symbol": symbol,
            },
        )
        start_time = time()

        try:
            data, _ = await asyncio.wait_for(
                asyncio.to_thread(self._ts.get_quote_endpoint, symbol),
                timeout=REQUEST_TIMEOUT,
            )

            if not data:
                raise ValueError(f"No price data available for {symbol}")

            # Alpha Vantage Global Quote keys (JSON format):
            # "01. symbol", "02. open", "03. high", "04. low", "05. price",
            # "06. volume", "07. latest trading day", "08. previous close",
            # "09. change", "10. change percent"
            price = data.get("05. price")
            if not price:
                raise ValueError(f"No price data available for {symbol}")

            change_pct_str = data.get("10. change percent", "0%")
            change_pct = change_pct_str.rstrip("%") if change_pct_str else None

            duration_ms = (time() - start_time) * 1000
            logger.info(
                "external_api_success",
                extra={
                    "provider": "alpha_vantage",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "price": price,
                },
            )

            return QuoteData(
                symbol=symbol.upper(),
                price=Decimal(str(price)),
                open=Decimal(str(data["02. open"])) if data.get("02. open") else None,
                high=Decimal(str(data["03. high"])) if data.get("03. high") else None,
                low=Decimal(str(data["04. low"])) if data.get("04. low") else None,
                volume=int(data["06. volume"]) if data.get("06. volume") else None,
                previous_close=Decimal(str(data["08. previous close"]))
                if data.get("08. previous close")
                else None,
                change=Decimal(str(data["09. change"]))
                if data.get("09. change")
                else None,
                change_percent=Decimal(change_pct) if change_pct else None,
            )

        except asyncio.TimeoutError:
            duration_ms = (time() - start_time) * 1000
            logger.error(
                "external_api_timeout",
                extra={
                    "provider": "alpha_vantage",
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
                    "provider": "alpha_vantage",
                    "operation": "get_quote",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to fetch quote for {symbol}: {e}")

    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """Get multiple quotes (sequential — conservative due to 25/day limit)."""
        logger.info(
            "external_api_call",
            extra={
                "provider": "alpha_vantage",
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
        """Get historical price data from Alpha Vantage."""
        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError as e:
            raise ValueError(str(e))

        logger.info(
            "external_api_call",
            extra={
                "provider": "alpha_vantage",
                "operation": "get_historical_prices",
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        start_time = time()

        try:
            # Choose the right endpoint based on interval
            if interval == "1wk":
                data, _ = await asyncio.wait_for(
                    asyncio.to_thread(self._ts.get_weekly, symbol),
                    timeout=REQUEST_TIMEOUT * 2,
                )
            elif interval == "1mo":
                data, _ = await asyncio.wait_for(
                    asyncio.to_thread(self._ts.get_monthly, symbol),
                    timeout=REQUEST_TIMEOUT * 2,
                )
            else:
                # Default: daily (use 'full' outputsize to get complete history)
                outputsize = "full" if (end_date - start_date).days > 100 else "compact"
                data, _ = await asyncio.wait_for(
                    asyncio.to_thread(self._ts.get_daily, symbol, outputsize=outputsize),
                    timeout=REQUEST_TIMEOUT * 2,
                )

            if not data:
                raise ValueError(f"No historical data for {symbol}")

            # Alpha Vantage returns dict keyed by date string
            # Keys: "1. open", "2. high", "3. low", "4. close", "5. volume"
            prices = []
            for date_str, values in sorted(data.items()):
                dt = date.fromisoformat(date_str)
                if start_date <= dt <= end_date:
                    prices.append(
                        HistoricalPrice(
                            date=dt,
                            open=Decimal(str(values["1. open"])),
                            high=Decimal(str(values["2. high"])),
                            low=Decimal(str(values["3. low"])),
                            close=Decimal(str(values["4. close"])),
                            volume=int(values["5. volume"]),
                            adjusted_close=Decimal(str(values["4. close"])),
                        )
                    )

            duration_ms = (time() - start_time) * 1000
            logger.info(
                "external_api_success",
                extra={
                    "provider": "alpha_vantage",
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
        """Search for symbols using Alpha Vantage symbol search."""
        try:
            data, _ = await asyncio.wait_for(
                asyncio.to_thread(self._ts.get_symbol_search, query),
                timeout=REQUEST_TIMEOUT,
            )

            if not data:
                return []

            results = []
            for item in data[:20]:
                # Keys: "1. symbol", "2. name", "3. type", "4. region",
                # "5. marketOpen", "6. marketClose", "7. timezone",
                # "8. currency", "9. matchScore"
                av_type = (item.get("3. type") or "").lower()
                type_map = {
                    "equity": "stock",
                    "etf": "etf",
                    "mutual fund": "mutual_fund",
                    "cryptocurrency": "crypto",
                }
                security_type = type_map.get(av_type, "stock")

                results.append(
                    SearchResult(
                        symbol=item.get("1. symbol", ""),
                        name=item.get("2. name", query),
                        type=security_type,
                        exchange=item.get("4. region"),
                        currency=item.get("8. currency"),
                    )
                )
            return results

        except Exception as e:
            logger.warning(f"Alpha Vantage symbol search failed for {query}: {e}")
            return []

    def supports_realtime(self) -> bool:
        """Alpha Vantage free tier does not provide real-time data."""
        return False

    def get_rate_limits(self) -> Dict[str, int]:
        return {"calls_per_minute": 5, "calls_per_day": 25}

    def get_provider_name(self) -> str:
        return "Alpha Vantage"
