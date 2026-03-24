"""API endpoints for enriching holdings with external data."""

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.holding import Holding
from app.models.user import User
from app.services.financial_data_service import financial_data_service
from app.services.rate_limit_service import rate_limit_service

router = APIRouter()


class EnrichmentResponse(BaseModel):
    """Response for enrichment request."""

    message: str
    enriched_count: int


class EnrichmentRequest(BaseModel):
    """Request to enrich holdings."""

    force_refresh: bool = False
    limit: int = Field(default=20, ge=1, le=200)


@router.post("/holdings/enrich", response_model=EnrichmentResponse)
async def enrich_holdings(
    request: EnrichmentRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enrich holdings with market cap and asset class data from external APIs.

    This endpoint fetches metadata for holdings that don't have it yet.
    Uses free APIs with rate limiting:
    - Alpha Vantage: 25 calls/day, 5/min
    - Finnhub: 60 calls/min (fallback)

    Data is cached for 7 days to minimize API calls.

    Args:
        force_refresh: If True, re-fetch even if holding already has data
        limit: Maximum number of holdings to enrich (default 20)

    Note: This runs synchronously with delays to respect rate limits.
          For large portfolios, expect ~4 minutes per 20 holdings.
    """
    # Rate-limit: calls external APIs and takes minutes to run (3/hr per user)
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=3,
        window_seconds=3600,
        identifier=str(current_user.id),
    )

    enriched_count = await financial_data_service.enrich_holdings_batch(
        db=db,
        organization_id=str(current_user.organization_id),
        limit=request.limit,
        force_refresh=request.force_refresh,
    )

    return EnrichmentResponse(
        message=f"Enriched {enriched_count} holdings with market cap data",
        enriched_count=enriched_count,
    )


@router.get("/holdings/enrichment-status")
async def get_enrichment_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get status of holding enrichment for the user's organization.

    Returns counts of enriched vs unenriched holdings.
    """
    # Count total equity holdings
    total_query = select(func.count(Holding.id)).where(
        Holding.organization_id == current_user.organization_id,
        Holding.asset_type.in_(["stock", "etf", "mutual_fund"]),
    )
    total_result = await db.execute(total_query)
    total_count = total_result.scalar() or 0

    # Count enriched holdings
    enriched_query = select(func.count(Holding.id)).where(
        Holding.organization_id == current_user.organization_id,
        Holding.asset_type.in_(["stock", "etf", "mutual_fund"]),
        Holding.market_cap.is_not(None),
        Holding.asset_class.is_not(None),
    )
    enriched_result = await db.execute(enriched_query)
    enriched_count = enriched_result.scalar() or 0

    unenriched_count = total_count - enriched_count

    return {
        "total_equity_holdings": total_count,
        "enriched": enriched_count,
        "unenriched": unenriched_count,
        "percent_enriched": (enriched_count / total_count * 100) if total_count > 0 else 0,
    }
