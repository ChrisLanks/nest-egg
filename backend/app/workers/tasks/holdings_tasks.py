"""Celery tasks for holdings snapshots and metadata enrichment."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal as async_session_factory
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import User
from app.models.holding import Holding
from app.services.market_data import get_market_data_provider
from app.services.snapshot_service import snapshot_service
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


@celery_app.task(name="enrich_holdings_metadata")
def enrich_holdings_metadata_task():
    """
    Enrich holdings with classification metadata from market data provider.

    Fetches sector, industry, asset_type, asset_class, market_cap, country,
    and name for every unique ticker and writes them back to the database.
    Only overwrites a field if the provider returned a non-null value, so
    manually set values are preserved when the API has no data.

    Runs daily at 7:00 PM EST (one hour after the price update).
    """
    asyncio.run(_enrich_metadata_async())


async def _enrich_metadata_async():
    """Async implementation of holdings metadata enrichment."""
    async with async_session_factory() as db:
        try:
            # Get all holdings that have a ticker
            result = await db.execute(select(Holding).where(Holding.ticker.isnot(None)))
            holdings = result.scalars().all()

            if not holdings:
                logger.info("No holdings to enrich")
                return

            # Build a mapping from ticker to the set of organization_ids that own it,
            # so the bulk update is scoped per-org (prevents cross-org metadata bleed
            # if two orgs happen to use the same custom ticker symbol).
            ticker_orgs: dict[str, set] = {}
            for h in holdings:
                key = h.ticker.upper()
                ticker_orgs.setdefault(key, set()).add(h.organization_id)

            tickers = list(ticker_orgs.keys())
            logger.info(f"Enriching metadata for {len(tickers)} unique tickers")

            market_data = get_market_data_provider()
            enriched_count = 0
            failed_count = 0

            for ticker in tickers:
                try:
                    metadata = await market_data.get_holding_metadata(ticker)

                    # Build update dict — only include fields the API returned a value for
                    updates: dict = {"updated_at": utc_now()}
                    if metadata.name is not None:
                        updates["name"] = metadata.name
                    if metadata.asset_type is not None:
                        updates["asset_type"] = metadata.asset_type
                    if metadata.asset_class is not None:
                        updates["asset_class"] = metadata.asset_class
                    if metadata.market_cap is not None:
                        updates["market_cap"] = metadata.market_cap
                    if metadata.sector is not None:
                        updates["sector"] = metadata.sector
                    if metadata.industry is not None:
                        updates["industry"] = metadata.industry
                    if metadata.country is not None:
                        updates["country"] = metadata.country

                    if len(updates) > 1:  # More than just updated_at
                        for org_id in ticker_orgs[ticker]:
                            await db.execute(
                                update(Holding)
                                .where(
                                    Holding.ticker == ticker,
                                    Holding.organization_id == org_id,
                                )
                                .values(**updates)
                            )
                        enriched_count += 1
                        logger.debug(f"Enriched {ticker}: {list(updates.keys())}")
                    else:
                        logger.debug(f"No metadata returned for {ticker}")

                except Exception as e:
                    logger.error(f"Error enriching metadata for {ticker}: {e}")
                    failed_count += 1

            await db.commit()

            logger.info(
                f"Holdings metadata enrichment complete. "
                f"Enriched: {enriched_count}, Failed: {failed_count}, "
                f"Total tickers: {len(tickers)} "
                f"(Provider: {market_data.get_provider_name()})"
            )

        except Exception as e:
            logger.error(f"Error in holdings metadata enrichment task: {str(e)}", exc_info=True)
            raise


@celery_app.task(name="capture_daily_holdings_snapshot")
def capture_daily_holdings_snapshot_task():
    """
    Capture daily holdings snapshot for all organizations.
    Runs daily at 11:59 PM to capture end-of-day values.
    """
    asyncio.run(_capture_snapshots_async())


async def _capture_snapshots_async():
    """Async implementation of holdings snapshot capture."""
    # Imported here to avoid circular dependency (holdings → services → tasks)
    from app.api.v1.holdings import get_portfolio_summary

    async with async_session_factory() as db:
        try:
            # Get all organizations
            result = await db.execute(select(User.organization_id).distinct())
            org_ids = [row[0] for row in result.all()]

            logger.info(f"Capturing holdings snapshots for {len(org_ids)} organizations")

            today = utc_now().date()
            total_snapshots = 0

            for org_id in org_ids:
                try:
                    # Idempotency check: skip if snapshot already captured today
                    # (e.g. by the orchestrate_portfolio_snapshots Celery task)
                    existing = await db.execute(
                        select(PortfolioSnapshot.id).where(
                            PortfolioSnapshot.organization_id == org_id,
                            PortfolioSnapshot.snapshot_date == today,
                        ).limit(1)
                    )
                    if existing.scalar_one_or_none():
                        logger.debug(f"Snapshot already exists for org {org_id} on {today}, skipping")
                        continue

                    # Get any user from this organization
                    user_result = await db.execute(
                        select(User).where(User.organization_id == org_id).limit(1)
                    )
                    user = user_result.scalar_one_or_none()

                    if not user:
                        logger.warning(f"No users found for org {org_id}")
                        continue

                    # Get current portfolio summary (this handles all the complex logic)
                    portfolio = await get_portfolio_summary(
                        user_id=None, current_user=user, db=db  # Get combined household view
                    )

                    # Capture snapshot for this organization
                    snapshot = await snapshot_service.capture_snapshot(
                        db=db, organization_id=org_id, portfolio=portfolio, snapshot_date=today
                    )

                    total_snapshots += 1
                    logger.info(f"Created snapshot for org {org_id}: ${snapshot.total_value:,.2f}")

                except Exception as e:
                    logger.error(
                        f"Error creating snapshot for org {org_id}: {str(e)}", exc_info=True
                    )
                    # Continue with other organizations

            logger.info(
                f"Holdings snapshot capture complete. Total snapshots created: {total_snapshots}"
            )

        except Exception as e:
            logger.error(f"Error in holdings snapshot task: {str(e)}", exc_info=True)
            raise


@celery_app.task(name="update_holdings_prices")
def update_holdings_prices_task():
    """
    Update prices for all holdings.
    Runs daily at 6:00 PM EST (after market close).
    """
    asyncio.run(_update_prices_async())


async def _update_prices_async():
    """
    Async implementation of holdings price update.

    Smart throttle: skips holdings whose price was refreshed within the last
    6 hours (e.g. by a user login).  This prevents Yahoo Finance from being
    hammered twice a day for active users while still covering orgs whose
    members haven't logged in.
    """
    STALE_AFTER_HOURS = 6
    cutoff = utc_now() - timedelta(hours=STALE_AFTER_HOURS)

    async with async_session_factory() as db:
        try:
            # Only fetch holdings whose price is stale or has never been fetched
            result = await db.execute(
                select(Holding).where(
                    Holding.ticker.isnot(None),
                    (Holding.price_as_of.is_(None)) | (Holding.price_as_of < cutoff),
                )
            )
            holdings = result.scalars().all()

            if not holdings:
                logger.info("All holdings prices are fresh — skipping daily update")
                return

            # Get unique tickers
            tickers = list({h.ticker for h in holdings if h.ticker})
            logger.info(
                f"Updating prices for {len(tickers)} stale tickers across {len(holdings)} holdings"
            )

            # Batch fetch quotes from market data provider
            market_data = get_market_data_provider()
            quotes = await market_data.get_quotes_batch(tickers)

            # Update holdings
            updated_count = 0
            skipped_count = 0
            now = datetime.now(timezone.utc)

            for holding in holdings:
                if holding.ticker in quotes:
                    try:
                        quote = quotes[holding.ticker]
                        await db.execute(
                            update(Holding)
                            .where(Holding.id == holding.id)
                            .values(
                                current_price_per_share=quote.price,
                                price_as_of=now,
                            )
                        )
                        updated_count += 1
                    except Exception as e:
                        logger.error(
                            f"Error updating holding {holding.id} ({holding.ticker}): {e}"
                        )
                else:
                    logger.warning(f"No quote available for {holding.ticker}")
                    skipped_count += 1

            await db.commit()

            logger.info(
                f"Holdings price update complete. "
                f"Updated: {updated_count}, Skipped: {skipped_count}, Total: {len(holdings)} "
                f"(Provider: {market_data.get_provider_name()})"
            )

        except Exception as e:
            logger.error(f"Error in holdings price update task: {str(e)}", exc_info=True)
            raise
