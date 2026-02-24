"""
Generic market data API endpoints.

Provider-agnostic - works with Yahoo Finance, Alpha Vantage, Finnhub, etc.
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from uuid import UUID
from datetime import date
from decimal import Decimal

import logging

from pydantic import BaseModel

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.holding import Holding
from app.services.market_data import (
    get_market_data_provider,
)
from app.core.rate_limiter import check_rate_limit, market_data_limiter
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
    check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

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


@router.post("/quote/batch", response_model=dict)
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
    check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

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
            ).model_dump()
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
    check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    validated = _validate_symbol(symbol)
    try:
        market_data = get_market_data_provider(provider)
        prices = await market_data.get_historical_prices(
            validated, start_date, end_date, interval
        )

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
    check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

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
    check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    market_data = get_market_data_provider(provider)

    return ProviderInfo(
        name=market_data.get_provider_name(),
        supports_realtime=market_data.supports_realtime(),
        rate_limits=market_data.get_rate_limits(),
    )


@router.post("/holdings/{holding_id}/refresh-price")
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
    check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

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
        quote = await market_data.get_quote(holding.symbol)

        # Update holding
        await db.execute(
            update(Holding)
            .where(Holding.id == holding_id)
            .values(
                current_price=quote.price,
                last_price_update=utc_now(),
            )
        )
        await db.commit()

        # Refresh holding
        await db.refresh(holding)

        return {
            "id": str(holding.id),
            "symbol": holding.symbol,
            "shares": float(holding.shares),
            "cost_basis": float(holding.cost_basis),
            "current_price": float(quote.price),
            "current_value": float(holding.shares * quote.price),
            "total_gain": float((holding.shares * quote.price) - holding.cost_basis),
            "provider": market_data.get_provider_name(),
        }

    except ValueError:
        raise HTTPException(status_code=404, detail="Symbol not found")
    except Exception as e:
        logger.error("Failed to refresh holding price: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refresh price")


@router.post("/holdings/refresh-all")
async def refresh_all_holdings(
    user_id: Optional[UUID] = Query(None, description="Specific user (admins only)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Refresh prices for all holdings in the organization.

    Returns count of updated holdings.
    """
    # Rate limit check
    check_rate_limit(str(current_user.id), market_data_limiter, "market_data")

    # Get all holdings
    query = select(Holding).where(Holding.organization_id == current_user.organization_id)

    if user_id:
        # Filter by user if specified
        query = query.join(Account).where(Account.user_id == user_id)

    result = await db.execute(query)
    holdings = result.scalars().all()

    if not holdings:
        return {"updated": 0, "message": "No holdings to update"}

    # Get unique symbols
    symbols = list(set(h.symbol for h in holdings))

    # Batch fetch quotes
    market_data = get_market_data_provider()
    quotes = await market_data.get_quotes_batch(symbols)

    # Update holdings
    updated_count = 0
    for holding in holdings:
        if holding.symbol in quotes:
            quote = quotes[holding.symbol]
            await db.execute(
                update(Holding)
                .where(Holding.id == holding.id)
                .values(
                    current_price=quote.price,
                    last_price_update=utc_now(),
                )
            )
            updated_count += 1

    await db.commit()

    return {
        "updated": updated_count,
        "total": len(holdings),
        "provider": market_data.get_provider_name(),
    }
