"""Celery tasks for banking provider transaction sync.

Moves transaction sync out of the webhook request path so:
- Webhooks return 200 immediately (Plaid/Teller won't retry)
- Sync failures are retried automatically by Celery (3x with backoff)
- Multiple concurrent webhooks are serialised by the existing Redis lock
- Worker pool can be scaled independently of the API server

Security: each task re-verifies that the organization_id parameter matches
the database record (defense-in-depth against accidental API bugs).
"""

import asyncio
import logging

from app.workers.celery_app import celery_app
from app.workers.utils import get_celery_session

logger = logging.getLogger(__name__)


async def _invalidate_org_caches(organization_id: str) -> None:
    """Invalidate all caches that depend on transaction data for an org."""
    from app.core.cache import delete_pattern as cache_delete_pattern

    await cache_delete_pattern(f"transactions:{organization_id}:*")
    await cache_delete_pattern(f"ie:*:{organization_id}:*")
    await cache_delete_pattern(f"dashboard:summary:{organization_id}:*")


# ---------------------------------------------------------------------------
# Plaid transaction sync
# ---------------------------------------------------------------------------


@celery_app.task(name="sync_plaid_transactions", bind=True, max_retries=3)
def sync_plaid_transactions_task(self, plaid_item_db_id: str, organization_id: str):
    """Background sync of Plaid transactions for a single PlaidItem.

    Args:
        plaid_item_db_id: The database UUID of the PlaidItem row (NOT the Plaid item_id).
        organization_id: Organization UUID (for cache invalidation + verification).
    """
    asyncio.run(_sync_plaid_transactions_async(plaid_item_db_id, organization_id))


async def _sync_plaid_transactions_async(plaid_item_db_id: str, organization_id: str):
    from uuid import UUID

    from sqlalchemy import select

    from app.models.account import PlaidItem
    from app.services.encryption_service import get_encryption_service
    from app.services.plaid_service import PlaidService
    from app.services.plaid_transaction_sync_service import PlaidTransactionSyncService

    async with get_celery_session() as db:
        try:
            result = await db.execute(
                select(PlaidItem).where(PlaidItem.id == UUID(plaid_item_db_id))
            )
            plaid_item = result.scalar_one_or_none()
            if not plaid_item:
                logger.warning("sync_plaid_transactions: PlaidItem %s not found", plaid_item_db_id)
                return

            # Defense-in-depth: verify org_id matches the database record
            if str(plaid_item.organization_id) != organization_id:
                logger.critical(
                    "sync_plaid_transactions: org mismatch! param=%s db=%s item=%s",
                    organization_id, plaid_item.organization_id, plaid_item_db_id,
                )
                return

            encryption_service = get_encryption_service()
            access_token = encryption_service.decrypt_token(plaid_item.access_token)

            plaid_service = PlaidService()
            transactions, removed_ids = await plaid_service.sync_transactions_real(
                access_token=access_token
            )

            sync_service = PlaidTransactionSyncService()
            stats = await sync_service.sync_transactions_for_item(
                db=db,
                plaid_item_id=plaid_item.id,
                transactions_data=transactions,
                is_test_mode=False,
            )

            if removed_ids:
                await sync_service.remove_transactions(
                    db=db,
                    plaid_item_id=plaid_item.id,
                    removed_transaction_ids=removed_ids,
                )

            # PlaidTransactionSyncService already invalidates caches on commit,
            # but ensure trend/dashboard caches are cleared too
            if stats.get("added", 0) > 0 or stats.get("updated", 0) > 0:
                await _invalidate_org_caches(organization_id)

            logger.info(
                "sync_plaid_transactions: item=%s added=%d updated=%d",
                plaid_item_db_id,
                stats.get("added", 0),
                stats.get("updated", 0),
            )

        except Exception as exc:
            logger.error("sync_plaid_transactions failed: %s", exc, exc_info=True)
            raise


# ---------------------------------------------------------------------------
# Teller transaction sync
# ---------------------------------------------------------------------------


@celery_app.task(name="sync_teller_transactions", bind=True, max_retries=3)
def sync_teller_transactions_task(self, account_db_id: str, organization_id: str, days_back: int = 7):
    """Background sync of Teller transactions for a single account.

    Args:
        account_db_id: The database UUID of the Account row.
        organization_id: Organization UUID (for cache invalidation + verification).
        days_back: Number of days of history to fetch.
    """
    asyncio.run(_sync_teller_transactions_async(account_db_id, organization_id, days_back))


async def _sync_teller_transactions_async(account_db_id: str, organization_id: str, days_back: int):
    from uuid import UUID

    from sqlalchemy import select

    from app.models.account import Account
    from app.services.teller_service import get_teller_service

    async with get_celery_session() as db:
        try:
            result = await db.execute(
                select(Account).where(Account.id == UUID(account_db_id))
            )
            account = result.scalar_one_or_none()
            if not account:
                logger.warning("sync_teller_transactions: Account %s not found", account_db_id)
                return

            # Defense-in-depth: verify org_id matches the database record
            if str(account.organization_id) != organization_id:
                logger.critical(
                    "sync_teller_transactions: org mismatch! param=%s db=%s account=%s",
                    organization_id, account.organization_id, account_db_id,
                )
                return

            teller_service = get_teller_service()
            await teller_service.sync_transactions(db, account, days_back=days_back)

            await _invalidate_org_caches(organization_id)

            logger.info(
                "sync_teller_transactions: account=%s days_back=%d",
                account_db_id,
                days_back,
            )

        except Exception as exc:
            logger.error("sync_teller_transactions failed: %s", exc, exc_info=True)
            raise


# ---------------------------------------------------------------------------
# MX transaction sync
# ---------------------------------------------------------------------------


@celery_app.task(name="sync_mx_transactions", bind=True, max_retries=3)
def sync_mx_transactions_task(self, account_db_id: str, organization_id: str, days_back: int = 90):
    """Background sync of MX transactions for a single account.

    Args:
        account_db_id: The database UUID of the Account row.
        organization_id: Organization UUID (for cache invalidation + verification).
        days_back: Number of days of history to fetch (MX default: 90).
    """
    asyncio.run(_sync_mx_transactions_async(account_db_id, organization_id, days_back))


async def _sync_mx_transactions_async(account_db_id: str, organization_id: str, days_back: int):
    from uuid import UUID

    from sqlalchemy import select

    from app.models.account import Account
    from app.services.mx_service import get_mx_service

    async with get_celery_session() as db:
        try:
            result = await db.execute(
                select(Account).where(Account.id == UUID(account_db_id))
            )
            account = result.scalar_one_or_none()
            if not account:
                logger.warning("sync_mx_transactions: Account %s not found", account_db_id)
                return

            # Defense-in-depth: verify org_id matches the database record
            if str(account.organization_id) != organization_id:
                logger.critical(
                    "sync_mx_transactions: org mismatch! param=%s db=%s account=%s",
                    organization_id, account.organization_id, account_db_id,
                )
                return

            mx_service = get_mx_service()
            await mx_service.sync_transactions(db, account, days_back=days_back)

            await _invalidate_org_caches(organization_id)

            logger.info(
                "sync_mx_transactions: account=%s days_back=%d",
                account_db_id,
                days_back,
            )

        except Exception as exc:
            logger.error("sync_mx_transactions failed: %s", exc, exc_info=True)
            raise
