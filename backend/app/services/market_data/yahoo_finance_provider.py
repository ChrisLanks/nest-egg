"""
Yahoo Finance market data provider.

FREE & UNLIMITED - Best for most users
- Stocks, ETFs, Mutual Funds, Crypto
- Real-time quotes (15-20 min delay for some exchanges)
- Historical data
- No API key required
"""

import yfinance as yf
import asyncio
from typing import Dict, List
from datetime import date
from decimal import Decimal
import logging

from .base_provider import (
    MarketDataProvider,
    QuoteData,
    HistoricalPrice,
    SearchResult,
)
from .security import (
    validate_symbol,
    validate_quote_response,
    SymbolValidationError,
    PriceValidationError,
)

logger = logging.getLogger(__name__)


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance implementation - FREE & UNLIMITED."""

    def __init__(self):
        """Initialize Yahoo Finance provider."""
        self.provider_name = "Yahoo Finance"

    async def get_quote(self, symbol: str) -> QuoteData:
        """Get current quote from Yahoo Finance."""
        # SECURITY: Validate symbol BEFORE making external API call
        try:
            symbol = validate_symbol(symbol)
        except SymbolValidationError as e:
            logger.error(f"Symbol validation failed: {e}")
            raise ValueError(str(e))

        try:
            # Run in thread pool to avoid blocking
            ticker = await asyncio.to_thread(yf.Ticker, symbol)
            info = await asyncio.to_thread(lambda: ticker.info)

            # Handle different response formats
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if current_price is None:
                # Try getting from history
                hist = await asyncio.to_thread(
                    lambda: ticker.history(period="1d")
                )
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])

            if current_price is None:
                raise ValueError(f"No price data available for {symbol}")

            # Build raw quote data
            raw_quote = {
                'symbol': symbol.upper(),
                'price': current_price,
                'name': info.get('longName') or info.get('shortName'),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange'),
                'volume': info.get('volume') or info.get('regularMarketVolume'),
                'market_cap': info.get('marketCap'),
                'change': info.get('regularMarketChange'),
                'change_percent': info.get('regularMarketChangePercent'),
                'previous_close': info.get('previousClose'),
                'open': info.get('open'),
                'high': info.get('dayHigh'),
                'low': info.get('dayLow'),
                'year_high': info.get('fiftyTwoWeekHigh'),
                'year_low': info.get('fiftyTwoWeekLow'),
                'dividend_yield': info.get('dividendYield'),
                'pe_ratio': info.get('trailingPE'),
            }

            # SECURITY: Validate response before returning
            validated = validate_quote_response(raw_quote, symbol)

            # Convert validated data to QuoteData
            return QuoteData(**validated.model_dump())

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol} from Yahoo Finance: {e}")
            raise ValueError(f"Failed to fetch quote for {symbol}: {str(e)}")

    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """Get multiple quotes efficiently."""
        quotes = {}

        # Yahoo Finance allows batch downloads
        try:
            symbols_str = " ".join(symbols)
            data = await asyncio.to_thread(
                yf.download,
                tickers=symbols_str,
                period="1d",
                group_by="ticker",
                progress=False,
                threads=True
            )

            # Parse results
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        # Single ticker - different structure
                        symbol_data = data
                    else:
                        # Multiple tickers
                        symbol_data = data[symbol]

                    if not symbol_data.empty:
                        latest = symbol_data.iloc[-1]
                        quotes[symbol] = QuoteData(
                            symbol=symbol.upper(),
                            price=Decimal(str(latest['Close'])),
                            open=Decimal(str(latest['Open'])),
                            high=Decimal(str(latest['High'])),
                            low=Decimal(str(latest['Low'])),
                            volume=int(latest['Volume']) if latest['Volume'] > 0 else None,
                            previous_close=Decimal(str(latest['Close'])),  # Approximation
                        )
                except Exception as e:
                    logger.warning(f"Error parsing quote for {symbol}: {e}")
                    # Try individual fetch as fallback
                    try:
                        quotes[symbol] = await self.get_quote(symbol)
                    except Exception:
                        pass  # Skip this symbol

        except Exception as e:
            logger.error(f"Batch download failed, falling back to individual fetches: {e}")
            # Fallback: fetch individually
            for symbol in symbols:
                try:
                    quotes[symbol] = await self.get_quote(symbol)
                except Exception:
                    pass  # Skip failed symbols

        return quotes

    async def get_historical_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> List[HistoricalPrice]:
        """Get historical price data."""
        try:
            ticker = await asyncio.to_thread(yf.Ticker, symbol)
            hist = await asyncio.to_thread(
                lambda: ticker.history(
                    start=start_date.isoformat(),
                    end=end_date.isoformat(),
                    interval=interval
                )
            )

            prices = []
            for idx, row in hist.iterrows():
                prices.append(
                    HistoricalPrice(
                        date=idx.date(),
                        open=Decimal(str(row['Open'])),
                        high=Decimal(str(row['High'])),
                        low=Decimal(str(row['Low'])),
                        close=Decimal(str(row['Close'])),
                        volume=int(row['Volume']),
                        adjusted_close=Decimal(str(row['Close'])),  # Yahoo provides adjusted
                    )
                )

            return prices

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            raise ValueError(f"Failed to fetch historical data for {symbol}: {str(e)}")

    async def search_symbol(self, query: str) -> List[SearchResult]:
        """
        Search for symbols.

        Note: Yahoo Finance doesn't have a native search API,
        so this is a basic implementation. For production,
        consider using Alpha Vantage or Finnhub for search.
        """
        # Basic implementation: try to get ticker info
        # For better search, use Alpha Vantage or Finnhub
        try:
            ticker = await asyncio.to_thread(yf.Ticker, query.upper())
            info = await asyncio.to_thread(lambda: ticker.info)

            if info.get('symbol'):
                return [
                    SearchResult(
                        symbol=info['symbol'],
                        name=info.get('longName') or info.get('shortName', query),
                        type=info.get('quoteType', 'stock').lower(),
                        exchange=info.get('exchange'),
                        currency=info.get('currency'),
                    )
                ]
        except Exception as e:
            logger.debug(f"Symbol search failed for {query}: {e}")

        return []

    def supports_realtime(self) -> bool:
        """Yahoo Finance provides near-real-time (15-20 min delay for some)."""
        return True

    def get_rate_limits(self) -> Dict[str, int]:
        """Yahoo Finance is free with soft rate limits."""
        return {
            'calls_per_minute': 0,  # Unlimited (soft limit)
            'calls_per_day': 0,      # Unlimited (soft limit)
            'note': 'Free with reasonable use limits'
        }

    def get_provider_name(self) -> str:
        """Get provider name."""
        return self.provider_name
