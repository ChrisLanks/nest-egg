"""
Financial data service for fetching market cap and security metadata.

Uses free APIs with aggressive caching to stay within rate limits:
- Alpha Vantage: 25 calls/day, 5/min (primary)
- Finnhub: 60 calls/min (backup)
"""

import asyncio
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core import cache
from app.config import settings
from app.models.holding import Holding

logger = logging.getLogger(__name__)


class FinancialDataService:
    """Service for fetching financial data with multiple API fallbacks."""

    def __init__(self):
        self.alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY if hasattr(settings, 'ALPHA_VANTAGE_API_KEY') else None
        self.finnhub_key = settings.FINNHUB_API_KEY if hasattr(settings, 'FINNHUB_API_KEY') else None
        self.cache_ttl = 86400 * 7  # 7 days for market cap data (changes rarely)

    async def get_security_metadata(
        self,
        ticker: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get security metadata including market cap classification.

        Returns:
            {
                'market_cap': 'large' | 'mid' | 'small',
                'asset_class': 'domestic' | 'international',
                'market_cap_value': Decimal (in billions),
                'sector': str,
                'industry': str,
            }
        """
        cache_key = f"security_metadata:{ticker}"

        # Check cache first
        if not force_refresh:
            cached = await cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for {ticker}")
                return cached

        # Try APIs in order
        metadata = None

        # Try Alpha Vantage first (more reliable, better data)
        if self.alpha_vantage_key:
            metadata = await self._fetch_from_alpha_vantage(ticker)

        # Fallback to Finnhub
        if not metadata and self.finnhub_key:
            metadata = await self._fetch_from_finnhub(ticker)

        # Cache the result if successful
        if metadata:
            await cache.setex(cache_key, self.cache_ttl, metadata)
            logger.info(f"Cached metadata for {ticker}")

        return metadata

    async def _fetch_from_alpha_vantage(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch from Alpha Vantage API.

        Uses OVERVIEW endpoint which returns company info including market cap.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://www.alphavantage.co/query"
                params = {
                    "function": "OVERVIEW",
                    "symbol": ticker,
                    "apikey": self.alpha_vantage_key,
                }

                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # Check for API errors
                if "Error Message" in data or "Note" in data:
                    logger.warning(f"Alpha Vantage error for {ticker}: {data}")
                    return None

                # Parse market cap
                market_cap_str = data.get("MarketCapitalization")
                if not market_cap_str:
                    return None

                market_cap_billions = Decimal(market_cap_str) / Decimal("1000000000")

                # Classify by market cap (in billions)
                if market_cap_billions >= 10:
                    cap_class = "large"
                elif market_cap_billions >= 2:
                    cap_class = "mid"
                else:
                    cap_class = "small"

                # Determine if domestic or international
                country = data.get("Country", "")
                asset_class = "domestic" if country == "USA" else "international"

                return {
                    "market_cap": cap_class,
                    "asset_class": asset_class,
                    "market_cap_value": float(market_cap_billions),
                    "sector": data.get("Sector"),
                    "industry": data.get("Industry"),
                    "country": country,
                    "source": "alpha_vantage",
                }

        except httpx.HTTPError as e:
            logger.error(f"Alpha Vantage HTTP error for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Alpha Vantage error for {ticker}: {e}")
            return None

    async def _fetch_from_finnhub(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch from Finnhub API.

        Uses profile2 endpoint which returns company profile including market cap.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://finnhub.io/api/v1/stock/profile2"
                params = {
                    "symbol": ticker,
                    "token": self.finnhub_key,
                }

                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # Finnhub returns empty object if not found
                if not data or "marketCapitalization" not in data:
                    return None

                # Market cap is in millions
                market_cap_billions = Decimal(str(data["marketCapitalization"])) / Decimal("1000")

                # Classify by market cap (in billions)
                if market_cap_billions >= 10:
                    cap_class = "large"
                elif market_cap_billions >= 2:
                    cap_class = "mid"
                else:
                    cap_class = "small"

                # Determine if domestic or international
                country = data.get("country", "")
                asset_class = "domestic" if country == "US" else "international"

                return {
                    "market_cap": cap_class,
                    "asset_class": asset_class,
                    "market_cap_value": float(market_cap_billions),
                    "sector": data.get("finnhubIndustry"),
                    "industry": data.get("finnhubIndustry"),
                    "country": country,
                    "source": "finnhub",
                }

        except httpx.HTTPError as e:
            logger.error(f"Finnhub HTTP error for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Finnhub error for {ticker}: {e}")
            return None

    async def enrich_holding(
        self,
        db: AsyncSession,
        holding: Holding,
        force_refresh: bool = False
    ) -> bool:
        """
        Enrich a holding with market cap and asset class data.

        Updates the holding in the database with fetched metadata.

        Returns:
            True if successfully enriched, False otherwise
        """
        # Skip if already enriched and not forcing refresh
        if not force_refresh and holding.market_cap and holding.asset_class:
            return True

        # Only enrich stocks and ETFs
        if holding.asset_type not in ['stock', 'etf', 'mutual_fund']:
            return False

        metadata = await self.get_security_metadata(holding.ticker, force_refresh)

        if not metadata:
            logger.info(f"No metadata found for {holding.ticker}")
            return False

        # Update holding
        try:
            holding.market_cap = metadata["market_cap"]
            holding.asset_class = metadata["asset_class"]
            holding.sector = metadata.get("sector")  # Persist sector data
            holding.industry = metadata.get("industry")  # Persist industry data
            holding.country = metadata.get("country")  # Persist country data for international categorization
            await db.commit()
            logger.info(f"Enriched {holding.ticker} with {metadata['market_cap']} {metadata['asset_class']} - {metadata.get('country', 'unknown')} - {metadata.get('sector', 'unknown sector')}")
            return True
        except Exception as e:
            logger.error(f"Failed to update holding {holding.ticker}: {e}")
            await db.rollback()
            return False

    async def enrich_holdings_batch(
        self,
        db: AsyncSession,
        organization_id: str,
        limit: int = 20,
        force_refresh: bool = False
    ) -> int:
        """
        Enrich multiple holdings in a batch with rate limiting.

        Processes up to `limit` holdings that need enrichment.
        Uses delays to respect API rate limits.

        Returns:
            Number of holdings successfully enriched
        """
        # Find holdings that need enrichment
        query = select(Holding).where(
            Holding.organization_id == organization_id,
            Holding.asset_type.in_(['stock', 'etf', 'mutual_fund'])
        )

        if not force_refresh:
            query = query.where(
                (Holding.market_cap == None) | (Holding.asset_class == None)
            )

        query = query.limit(limit)
        result = await db.execute(query)
        holdings = result.scalars().all()

        if not holdings:
            logger.info("No holdings need enrichment")
            return 0

        logger.info(f"Enriching {len(holdings)} holdings")

        enriched_count = 0
        for holding in holdings:
            success = await self.enrich_holding(db, holding, force_refresh)
            if success:
                enriched_count += 1

            # Rate limiting: wait 12 seconds between calls (5 calls/min for Alpha Vantage)
            if self.alpha_vantage_key:
                await asyncio.sleep(12)
            else:
                # Finnhub is more generous, 1 second delay is fine
                await asyncio.sleep(1)

        logger.info(f"Successfully enriched {enriched_count}/{len(holdings)} holdings")
        return enriched_count


# Singleton instance
financial_data_service = FinancialDataService()
