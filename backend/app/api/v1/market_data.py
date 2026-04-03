"""
Generic market data API endpoints.

Provider-agnostic - works with Yahoo Finance, Alpha Vantage, Finnhub, etc.
"""

import logging
import re
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limiter import check_rate_limit, market_data_limiter
from app.dependencies import get_current_user, verify_household_member
from app.models.account import Account
from app.models.holding import Holding
from app.models.user import User
from app.services.market_data import (
    get_market_data_provider,
)
from app.services.market_data.cache import invalidate_quotes
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class QuoteResponse(BaseModel):
    """Quote data response."""

    symbol: str
    price: Decimal
    name: Optional[str] = None
    currency: str = "USD"
    exchange: Optional[str] = None
    volume: Optional[int] = None
    market_cap: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    year_high: Optional[Decimal] = None
    year_low: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    provider: str  # Which provider was used


class HoldingWithQuote(BaseModel):
    """Holding with current quote data."""

    id: UUID
    symbol: str
    shares: Decimal
    cost_basis: Decimal
    current_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    total_gain: Optional[Decimal] = None
    total_gain_percent: Optional[Decimal] = None
    day_change: Optional[Decimal] = None
    day_change_percent: Optional[Decimal] = None
    quote: Optional[QuoteResponse] = None


class HistoricalPriceResponse(BaseModel):
    """Historical price response."""

    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Optional[Decimal] = None


class SearchResultResponse(BaseModel):
    """Search result response."""

    symbol: str
    name: str
    type: str
    exchange: Optional[str] = None
    currency: Optional[str] = None


class ProviderInfo(BaseModel):
    """Provider information."""

    name: str
    supports_realtime: bool
    rate_limits: dict


class HoldingRefreshResponse(BaseModel):
    """Response for a single holding price refresh."""

    id: str
    symbol: str
    shares: float
    cost_basis: float
    current_price: float
    current_value: float
    total_gain: float
    provider: str


class HoldingRefreshAllResponse(BaseModel):
    """Response for bulk holding price refresh."""

    updated: int
    total: int
    provider: str


# ============================================================================
# Helpers
# ============================================================================

# Valid ticker format: 1-15 uppercase alphanumeric chars plus ., -, ^
# Covers stocks (AAPL), ETFs (BRK.A), indices (^GSPC), crypto (BTC-USD).
_TICKER_RE = re.compile(r"^[A-Z0-9.\-\^]{1,15}$")


def _validate_symbol(symbol: str) -> str:
    """Normalise and validate a ticker symbol. Raises 400 on invalid format."""
    upper = symbol.strip().upper()
    if not _TICKER_RE.match(upper):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ticker symbol '{symbol}'. "
            "Must be 1-15 characters: letters, digits, '.', '-', or '^'.",
        )
    return upper


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str,
    provider: Optional[str] = Query(
        None, description="Override provider (yahoo_finance, alpha_vantage, finnhub)"
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Get current quote for any symbol.

    Works with stocks, ETFs, mutual funds, crypto, etc.
    """
    # Rate limit check
    await check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    validated = _validate_symbol(symbol)
    try:
        market_data = get_market_data_provider(provider)
        quote = await market_data.get_quote(validated)

        return QuoteResponse(**quote.model_dump(), provider=market_data.get_provider_name())

    except ValueError:
        raise HTTPException(status_code=404, detail="Symbol not found")
    except Exception as e:
        logger.error("Failed to fetch quote for %s: %s", validated, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch quote")


MAX_BATCH_SYMBOLS = 50


@router.post("/quote/batch", response_model=Dict[str, QuoteResponse])
async def get_quotes_batch(
    symbols: List[str],
    provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Get quotes for multiple symbols efficiently.

    Returns dict mapping symbol to quote data.
    """
    # Rate limit check
    await check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    if len(symbols) > MAX_BATCH_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many symbols. Maximum is {MAX_BATCH_SYMBOLS}.",
        )

    validated = [_validate_symbol(s) for s in symbols]
    try:
        market_data = get_market_data_provider(provider)
        quotes = await market_data.get_quotes_batch(validated)

        return {
            symbol: QuoteResponse(
                **quote.model_dump(), provider=market_data.get_provider_name()
            )
            for symbol, quote in quotes.items()
        }

    except Exception as e:
        logger.error("Failed to fetch batch quotes: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch quotes")


@router.get("/historical/{symbol}", response_model=List[HistoricalPriceResponse])
async def get_historical_prices(
    symbol: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    interval: str = Query("1d", description="Interval (1d, 1wk, 1mo)"),
    provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get historical price data for charts."""
    # Rate limit check
    await check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    validated = _validate_symbol(symbol)
    try:
        market_data = get_market_data_provider(provider)
        prices = await market_data.get_historical_prices(validated, start_date, end_date, interval)

        return [HistoricalPriceResponse(**p.model_dump()) for p in prices]

    except ValueError:
        raise HTTPException(status_code=404, detail="Symbol not found")
    except Exception as e:
        logger.error("Failed to fetch historical data for %s: %s", validated, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch historical data")


@router.get("/search", response_model=List[SearchResultResponse])
async def search_symbols(
    query: str = Query(..., min_length=1, description="Search query (symbol or company name)"),
    provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Search for stocks/securities by name or symbol."""
    # Rate limit check
    await check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    try:
        market_data = get_market_data_provider(provider)
        results = await market_data.search_symbol(query)

        return [SearchResultResponse(**r.model_dump()) for r in results]

    except Exception as e:
        logger.error("Symbol search failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/provider-info", response_model=ProviderInfo)
async def get_provider_info(
    provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get information about the current market data provider."""
    # Rate limit check
    await check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    market_data = get_market_data_provider(provider)

    return ProviderInfo(
        name=market_data.get_provider_name(),
        supports_realtime=market_data.supports_realtime(),
        rate_limits=market_data.get_rate_limits(),
    )


@router.post("/holdings/{holding_id}/refresh-price", response_model=HoldingRefreshResponse)
async def refresh_holding_price(
    holding_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Refresh price for a specific holding.

    Updates current_price and last_price_update fields.
    """
    # Rate limit check
    await check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    # Get holding
    result = await db.execute(
        select(Holding).where(
            Holding.id == holding_id,
            Holding.organization_id == current_user.organization_id,
        )
    )
    holding = result.scalar_one_or_none()

    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    try:
        # Get quote
        market_data = get_market_data_provider()
        quote = await market_data.get_quote(holding.ticker)

        # Update holding
        await db.execute(
            update(Holding)
            .where(Holding.id == holding_id, Holding.organization_id == current_user.organization_id)
            .values(
                current_price_per_share=quote.price,
                price_as_of=utc_now(),
            )
        )
        await db.commit()
        await invalidate_quotes(holding.ticker)

        # Refresh holding
        await db.refresh(holding)

        cost_basis = holding.total_cost_basis or Decimal(0)
        return {
            "id": str(holding.id),
            "symbol": holding.ticker,
            "shares": float(holding.shares),
            "cost_basis": float(cost_basis),
            "current_price": float(quote.price),
            "current_value": float(holding.shares * quote.price),
            "total_gain": float((holding.shares * quote.price) - cost_basis),
            "provider": market_data.get_provider_name(),
        }

    except ValueError:
        raise HTTPException(status_code=404, detail="Symbol not found")
    except Exception as e:
        logger.error("Failed to refresh holding price: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refresh price")


@router.post("/holdings/refresh-all", response_model=HoldingRefreshAllResponse)
async def refresh_all_holdings(
    user_id: Optional[UUID] = Query(None, description="Filter by user within organization"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Refresh prices for all holdings in the organization.

    Returns count of updated holdings.
    """
    # Rate limit check
    await check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    # Get all holdings
    query = select(Holding).where(Holding.organization_id == current_user.organization_id)

    if user_id:
        # Filter by user if specified
        query = query.join(Account).where(Account.user_id == user_id)

    result = await db.execute(query)
    holdings = result.scalars().all()

    if not holdings:
        return HoldingRefreshAllResponse(updated=0, total=0, provider="none")

    # Get unique symbols
    symbols = list(set(h.ticker for h in holdings))

    # Batch fetch quotes from market data provider
    market_data = get_market_data_provider()
    quotes = await market_data.get_quotes_batch(symbols)

    # Build mapping: symbol -> price, then batch update per symbol
    now = utc_now()
    updated_count = 0
    for symbol, quote in quotes.items():
        result = await db.execute(
            update(Holding)
            .where(
                Holding.organization_id == current_user.organization_id,
                Holding.ticker == symbol,
            )
            .values(
                current_price_per_share=quote.price,
                price_as_of=now,
            )
        )
        updated_count += result.rowcount

    await db.commit()
    await invalidate_quotes(*symbols)

    return {
        "updated": updated_count,
        "total": len(holdings),
        "provider": market_data.get_provider_name(),
    }


# ── Crypto price batch endpoint ───────────────────────────────────────────────


class CryptoPriceItem(BaseModel):
    """Price data for a single crypto asset."""

    symbol: str
    price: Decimal
    change_percent: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    volume: Optional[int] = None
    provider: str


@router.get("/crypto/prices", response_model=list[CryptoPriceItem])
async def get_crypto_prices(
    symbols: str = Query(
        ...,
        description="Comma-separated list of crypto symbols, e.g. BTC-USD,ETH-USD,SOL-USD",
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Get current prices for one or more crypto symbols.

    Always uses the CoinGecko provider (free, no API key required) regardless
    of the configured MARKET_DATA_PROVIDER setting.

    Symbols should use the Yahoo-style format: BTC-USD, ETH-USD, etc.
    Bare tickers like BTC and ETH are also accepted.
    """
    await check_rate_limit(str(current_user.id), market_data_limiter, "crypto_prices")

    raw_symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not raw_symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")
    if len(raw_symbols) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 symbols per request")

    # Validate each symbol
    validated = []
    for sym in raw_symbols:
        try:
            validated.append(_validate_symbol(sym))
        except HTTPException:
            pass  # Skip invalid symbols gracefully

    if not validated:
        raise HTTPException(status_code=400, detail="No valid symbols provided")

    # Always use CoinGecko for crypto
    from app.config import settings as _settings
    from app.services.market_data.coingecko_provider import CoinGeckoProvider

    provider = CoinGeckoProvider(api_key=_settings.COINGECKO_API_KEY)
    quotes = await provider.get_quotes_batch(validated)

    results = []
    for sym in validated:
        quote = quotes.get(sym)
        if quote:
            results.append(
                CryptoPriceItem(
                    symbol=sym,
                    price=quote.price,
                    change_percent=quote.change_percent,
                    market_cap=quote.market_cap,
                    volume=quote.volume,
                    provider=provider.get_provider_name(),
                )
            )

    return results
