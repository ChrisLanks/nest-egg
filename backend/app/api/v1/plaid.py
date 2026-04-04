"""Plaid integration API endpoints."""

import hashlib
import json as _json
import logging
import uuid as _uuid_module
from datetime import timedelta
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountSource, AccountType, PlaidItem, TaxTreatment
from app.models.notification import NotificationPriority, NotificationType
from app.models.user import Organization, User
from app.schemas.plaid import (
    LinkTokenCreateRequest,
    LinkTokenCreateResponse,
    PlaidAccount,
    PublicTokenExchangeRequest,
    PublicTokenExchangeResponse,
)
from app.services.deduplication_service import DeduplicationService
from app.services.encryption_service import get_encryption_service
from app.services.notification_service import notification_service
from app.services.plaid_holdings_sync_service import plaid_holdings_sync_service
from app.services.plaid_service import PlaidService
from app.services.plaid_transaction_sync_service import (
    MockPlaidTransactionGenerator,
    PlaidTransactionSyncService,
)
from app.core.cache import setnx_with_ttl as cache_setnx
from app.services.rate_limit_service import rate_limit_service
from app.utils.account_type_groups import PLAID_EXCLUDE_CASH_FLOW_TYPES
from app.utils.datetime_utils import utc_now

# Webhook deduplication TTL — 24 hours
_WEBHOOK_DEDUP_TTL = 86_400

router = APIRouter()
logger = logging.getLogger(__name__)
deduplication_service = DeduplicationService()
encryption_service = get_encryption_service()


@router.post("/link-token", response_model=LinkTokenCreateResponse)
async def create_link_token(
    request: LinkTokenCreateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Plaid Link token for initiating the Plaid Link flow.
    Rate limited to 10 requests per minute to prevent API quota abuse.

    For test@test.com users, returns a dummy token.
    """
    # Rate limit: 10 link token requests per minute per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=60,
        identifier=str(current_user.id),
    )

    plaid_service = PlaidService()

    try:
        link_token, expiration = await plaid_service.create_link_token(current_user)

        return LinkTokenCreateResponse(
            link_token=link_token,
            expiration=expiration,
        )
    except Exception as e:
        logger.error(f"Failed to create link token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create link token")


@router.post("/exchange-token", response_model=PublicTokenExchangeResponse)
async def exchange_public_token(
    request: PublicTokenExchangeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a Plaid public token for an access token and create accounts.
    Rate limited to 5 requests per minute to prevent token exchange abuse.

    For test@test.com users, creates accounts with dummy data.
    """
    # Rate limit: 5 token exchanges per minute per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=60,
        identifier=str(current_user.id),
    )

    plaid_service = PlaidService()

    try:
        # Exchange public token for access token and get accounts
        access_token, plaid_accounts = await plaid_service.exchange_public_token(
            user=current_user,
            public_token=request.public_token,
            institution_id=request.institution_id,
            institution_name=request.institution_name,
            accounts_metadata=request.accounts,
        )

        # Create PlaidItem record
        # Encrypt the access token before storing
        encrypted_access_token = encryption_service.encrypt_token(access_token)

        plaid_item = PlaidItem(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            item_id=f"item_{_uuid_module.uuid4().hex}",  # Random ID — never exposes token content
            access_token=encrypted_access_token,  # Store encrypted
            institution_id=request.institution_id,
            institution_name=request.institution_name or "Unknown Institution",
        )
        db.add(plaid_item)
        await db.flush()  # Flush to get the plaid_item.id

        # Create Account records for each Plaid account
        created_accounts: List[PlaidAccount] = []

        for plaid_account in plaid_accounts:
            # Map Plaid account type to our AccountType enum and tax treatment
            account_type, tax_treatment = _map_plaid_account_type(
                plaid_account.get("type"),
                plaid_account.get("subtype"),
            )

            # Generate hash for deduplication across household members
            plaid_item_hash = deduplication_service.calculate_plaid_hash(
                plaid_item.item_id, plaid_account["account_id"]
            )

            # Determine if account should be excluded from cash flow by default
            # Loans and mortgages are excluded to prevent double-counting
            # Credit cards are INCLUDED - we want to see purchases,
            # and payments are filtered via is_transfer
            exclude_from_cash_flow = account_type in PLAID_EXCLUDE_CASH_FLOW_TYPES

            account = Account(
                organization_id=current_user.organization_id,
                user_id=current_user.id,
                plaid_item_id=plaid_item.id,
                external_account_id=plaid_account["account_id"],
                name=plaid_account["name"],
                account_type=account_type,
                tax_treatment=tax_treatment,
                account_source=AccountSource.PLAID,
                institution_name=request.institution_name or "Unknown Institution",
                mask=plaid_account.get("mask"),
                plaid_item_hash=plaid_item_hash,
                current_balance=plaid_account.get("current_balance"),
                available_balance=plaid_account.get("available_balance"),
                limit=plaid_account.get("limit"),
                is_manual=False,
                is_active=True,
                exclude_from_cash_flow=exclude_from_cash_flow,
            )
            db.add(account)

            created_accounts.append(
                PlaidAccount(
                    account_id=plaid_account["account_id"],
                    name=plaid_account["name"],
                    mask=plaid_account.get("mask"),
                    official_name=plaid_account.get("official_name"),
                    type=plaid_account["type"],
                    subtype=plaid_account.get("subtype"),
                    current_balance=plaid_account.get("current_balance", 0),
                    available_balance=plaid_account.get("available_balance"),
                    limit=plaid_account.get("limit"),
                )
            )

        await db.commit()

        # Notify all household members that new accounts were connected
        institution = request.institution_name or "Unknown Institution"
        user_name = current_user.display_name or current_user.first_name or current_user.email
        await notification_service.create_notification(
            db=db,
            organization_id=current_user.organization_id,
            type=NotificationType.ACCOUNT_CONNECTED,
            title=f"New account connected: {institution}",
            message=(
                f"{user_name} connected {len(created_accounts)} account(s) "
                f"from {institution} via Plaid."
            ),
            priority=NotificationPriority.LOW,
            action_url="/accounts",
            action_label="View Accounts",
            expires_in_days=14,
        )

        return PublicTokenExchangeResponse(
            item_id=plaid_item.item_id,
            accounts=created_accounts,
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to exchange token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to exchange token")


def _map_plaid_account_type(
    plaid_type: str, plaid_subtype: str
) -> tuple[AccountType, TaxTreatment | None]:
    """Map Plaid account type/subtype to our AccountType enum and TaxTreatment.

    Returns (account_type, tax_treatment). tax_treatment is None for
    non-retirement accounts.
    """
    # https://plaid.com/docs/api/accounts/#account-type-schema

    if plaid_type == "depository":
        if plaid_subtype == "checking":
            return AccountType.CHECKING, None
        elif plaid_subtype == "savings":
            return AccountType.SAVINGS, None
        else:
            return AccountType.CHECKING, None

    elif plaid_type == "credit":
        if plaid_subtype == "credit_card":
            return AccountType.CREDIT_CARD, None
        else:
            return AccountType.LOAN, None

    elif plaid_type == "loan":
        if plaid_subtype in ["mortgage", "home_equity"]:
            return AccountType.MORTGAGE, None
        elif plaid_subtype == "student":
            return AccountType.STUDENT_LOAN, None
        else:
            return AccountType.LOAN, None

    elif plaid_type == "investment":
        # Traditional employer-sponsored retirement
        if plaid_subtype == "401k":
            return AccountType.RETIREMENT_401K, TaxTreatment.PRE_TAX
        elif plaid_subtype == "403b":
            return AccountType.RETIREMENT_403B, TaxTreatment.PRE_TAX
        elif plaid_subtype == "457b":
            return AccountType.RETIREMENT_457B, TaxTreatment.PRE_TAX
        # Traditional IRA variants
        elif plaid_subtype in ["ira", "traditional_ira"]:
            return AccountType.RETIREMENT_IRA, TaxTreatment.PRE_TAX
        elif plaid_subtype == "sep_ira":
            return AccountType.RETIREMENT_SEP_IRA, TaxTreatment.PRE_TAX
        elif plaid_subtype == "simple_ira":
            return AccountType.RETIREMENT_SIMPLE_IRA, TaxTreatment.PRE_TAX
        # Roth variants
        elif plaid_subtype in ["roth", "roth_ira"]:
            return AccountType.RETIREMENT_ROTH, TaxTreatment.ROTH
        elif plaid_subtype == "roth_401k":
            return AccountType.RETIREMENT_401K, TaxTreatment.ROTH
        elif plaid_subtype == "roth_403b":
            return AccountType.RETIREMENT_403B, TaxTreatment.ROTH
        # Tax-advantaged
        elif plaid_subtype == "hsa":
            return AccountType.HSA, TaxTreatment.TAX_FREE
        elif plaid_subtype in ["529", "education_savings"]:
            return AccountType.RETIREMENT_529, TaxTreatment.TAX_FREE
        # Taxable
        elif plaid_subtype == "brokerage":
            return AccountType.BROKERAGE, TaxTreatment.TAXABLE
        else:
            return AccountType.BROKERAGE, TaxTreatment.TAXABLE

    else:
        return AccountType.OTHER, None


@router.post("/sync-holdings/{account_id}", response_model=Dict[str, Any])
async def sync_plaid_holdings(
    account_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync investment holdings from Plaid for a specific account.
    Rate limited to 5 requests per minute to prevent excessive syncing.

    Fetches the latest holdings data from Plaid and upserts them into the
    local holdings table.
    """
    # Rate limit: 5 holdings sync requests per minute per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=60,
        identifier=str(current_user.id),
    )

    # Fetch account and verify ownership
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Verify it's a Plaid-linked account
    if not account.plaid_item_id:
        raise HTTPException(
            status_code=400,
            detail="Account is not linked via Plaid",
        )

    # Get the PlaidItem to retrieve the access token
    plaid_item_result = await db.execute(
        select(PlaidItem).where(
            PlaidItem.id == account.plaid_item_id,
            PlaidItem.organization_id == current_user.organization_id,
        )
    )
    plaid_item = plaid_item_result.scalar_one_or_none()

    if not plaid_item:
        raise HTTPException(status_code=404, detail="Plaid item not found")

    try:
        # Decrypt access token
        access_token = encryption_service.decrypt_token(plaid_item.access_token)

        # Fetch holdings from Plaid
        plaid_service = PlaidService()
        holdings, securities = await plaid_service.get_investment_holdings(
            user=current_user,
            access_token=access_token,
        )

        # Sync holdings into local database
        count = await plaid_holdings_sync_service.sync_holdings(
            db=db,
            account=account,
            plaid_holdings=holdings,
            plaid_securities=securities,
        )

        return {
            "success": True,
            "synced": count,
            "account_id": str(account_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Holdings sync error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Holdings sync failed")


@router.post("/webhook", response_model=Dict[str, Any])
async def handle_plaid_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle webhook notifications from Plaid.
    Rate limited to 20 requests per minute to prevent abuse.

    Plaid sends webhooks for various events like:
    - ITEM_ERROR: Item encounters an error
    - PENDING_EXPIRATION: Item access token is about to expire
    - USER_PERMISSION_REVOKED: User revoked permission
    - DEFAULT_UPDATE: General account updates
    """
    # Rate limit: 20 webhook requests per minute per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=20,
        window_seconds=60,
    )

    try:
        # Read raw body BEFORE parsing — verify signature on untrusted data first
        raw_body = await request.body()

        # Verify webhook signature to ensure it's from Plaid
        plaid_verification_header = request.headers.get("Plaid-Verification")
        await PlaidService.verify_webhook_signature(
            webhook_verification_header=plaid_verification_header, webhook_body=raw_body
        )

        # Only parse JSON after signature is verified
        webhook_data: Dict[str, Any] = _json.loads(raw_body)

        webhook_type = webhook_data.get("webhook_type")
        webhook_code = webhook_data.get("webhook_code")
        item_id = webhook_data.get("item_id")

        # Dedup: hash the body to detect retried webhooks (Plaid may retry on timeout)
        body_hash = hashlib.sha256(raw_body).hexdigest()[:16]
        dedup_key = f"plaid:webhook:dedup:{body_hash}"
        is_new = await cache_setnx(dedup_key, _WEBHOOK_DEDUP_TTL)
        if not is_new:
            logger.info(
                "Plaid webhook duplicate skipped: %s - %s (hash=%s)",
                webhook_type, webhook_code, body_hash,
            )
            return {"status": "duplicate_skipped"}

        logger.info(f"Plaid webhook received: {webhook_type} - {webhook_code}")

        # Get PlaidItem — the item_id in the payload is attacker-controlled (only
        # the Plaid-Verification signature is trusted). Scoping to item_id alone
        # is fine here because Plaid signs webhooks per-item and item_ids are
        # opaque non-guessable strings. We log if the item is missing so
        # operations on stale/deleted items are visible in logs.
        result = await db.execute(select(PlaidItem).where(PlaidItem.item_id == item_id))
        plaid_item = result.scalar_one_or_none()

        if not plaid_item:
            logger.warning(
                "Plaid webhook: item_id %s not found (webhook_type=%s webhook_code=%s) — "
                "item may have been deleted or never linked",
                item_id,
                webhook_type,
                webhook_code,
            )
            return {"status": "item_not_found"}

        # Handle different webhook types
        if webhook_type == "ITEM":
            await _handle_item_webhook(db, plaid_item, webhook_code, webhook_data)
        elif webhook_type == "TRANSACTIONS":
            await _handle_transactions_webhook(db, plaid_item, webhook_code, webhook_data)
        elif webhook_type == "AUTH":
            await _handle_auth_webhook(db, plaid_item, webhook_code, webhook_data)
        else:
            logger.warning(
                "Unhandled Plaid webhook type=%r code=%r — may need a handler",
                webhook_type,
                webhook_code,
            )

        return {"status": "acknowledged"}

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/sync-transactions/{plaid_item_id}", response_model=Dict[str, Any])
async def sync_transactions(
    plaid_item_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger transaction sync for a Plaid item.
    Rate limited to 5 requests per minute to prevent excessive syncing.

    Useful for:
    - Initial sync after linking accounts
    - Manual refresh
    - Testing
    """
    # Rate limit: 5 sync requests per minute per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=60,
        identifier=str(current_user.id),
    )

    # Get PlaidItem and verify ownership
    result = await db.execute(
        select(PlaidItem).where(
            PlaidItem.id == plaid_item_id, PlaidItem.organization_id == current_user.organization_id
        )
    )
    plaid_item = result.scalar_one_or_none()

    if not plaid_item:
        raise HTTPException(status_code=404, detail="Plaid item not found")

    try:
        # Check if test user
        is_test_user = current_user.email == "test@test.com"

        if is_test_user:
            # Generate mock transaction data for test users
            logger.info("Generating mock transactions for test user")

            # Get accounts for this plaid_item
            accounts_result = await db.execute(
                select(Account).where(Account.plaid_item_id == plaid_item.id)
            )
            accounts = accounts_result.scalars().all()

            if not accounts:
                raise HTTPException(status_code=400, detail="No accounts found for this Plaid item")

            # Generate transactions for each account
            all_transactions = []
            end_date = utc_now().date()
            start_date = end_date - timedelta(days=90)  # Last 3 months

            for account in accounts:
                mock_transactions = MockPlaidTransactionGenerator.generate_mock_transactions(
                    account_id=account.external_account_id,
                    start_date=start_date,
                    end_date=end_date,
                    count=30,  # 30 transactions per account
                )
                all_transactions.extend(mock_transactions)

            # Sync transactions
            sync_service = PlaidTransactionSyncService()
            stats = await sync_service.sync_transactions_for_item(
                db=db,
                plaid_item_id=plaid_item.id,
                transactions_data=all_transactions,
                is_test_mode=True,
            )

            return {
                "success": True,
                "message": "Mock transactions synced successfully",
                "stats": stats,
                "is_test_mode": True,
            }
        else:
            # Real Plaid transaction sync
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
                removed = await sync_service.remove_transactions(
                    db=db,
                    plaid_item_id=plaid_item.id,
                    removed_transaction_ids=removed_ids,
                )
                stats["removed"] = removed

            return {
                "success": True,
                "message": "Transactions synced successfully",
                "stats": stats,
                "is_test_mode": False,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Sync failed")


async def _handle_item_webhook(
    db: AsyncSession,
    plaid_item: PlaidItem,
    webhook_code: str,
    webhook_data: Dict[str, Any],
):
    """Handle ITEM webhook events."""
    error_data = webhook_data.get("error")

    if webhook_code == "ERROR":
        # Item encountered an error
        error_code = error_data.get("error_code") if error_data else "UNKNOWN"
        error_message = error_data.get("error_message") if error_data else "Unknown error"

        # Check if reauth is required
        needs_reauth = error_code in ["ITEM_LOGIN_REQUIRED", "PENDING_EXPIRATION"]

        # Get first account for this item to get account details
        result = await db.execute(
            select(Account).where(Account.plaid_item_id == plaid_item.id).limit(1)
        )
        account = result.scalar_one_or_none()

        if account:
            await notification_service.create_account_sync_notification(
                db=db,
                organization_id=plaid_item.organization_id,
                account_id=account.id,
                account_name=plaid_item.institution_name,
                error_message=error_message,
                needs_reauth=needs_reauth,
            )

    elif webhook_code == "PENDING_EXPIRATION":
        # Item access token is about to expire
        await notification_service.create_notification(
            db=db,
            organization_id=plaid_item.organization_id,
            type=NotificationType.REAUTH_REQUIRED,
            title=f"Reconnect {plaid_item.institution_name}",
            message=(
                f"Your connection to {plaid_item.institution_name}"
                " will expire soon. Please reconnect to"
                " continue syncing."
            ),
            priority=NotificationPriority.HIGH,
            related_entity_type="plaid_item",
            related_entity_id=plaid_item.id,
            action_url="/accounts",
            action_label="Reconnect",
            expires_in_days=7,
        )

    elif webhook_code == "USER_PERMISSION_REVOKED":
        # User revoked permission - mark item as inactive
        plaid_item.is_active = False
        await db.commit()

        await notification_service.create_notification(
            db=db,
            organization_id=plaid_item.organization_id,
            type=NotificationType.ACCOUNT_ERROR,
            title=f"Connection Revoked: {plaid_item.institution_name}",
            message=(
                f"Access to {plaid_item.institution_name}"
                " has been revoked. Reconnect to continue"
                " syncing."
            ),
            priority=NotificationPriority.HIGH,
            related_entity_type="plaid_item",
            related_entity_id=plaid_item.id,
            action_url="/accounts",
            action_label="Reconnect",
            expires_in_days=7,
        )


async def _handle_transactions_webhook(
    db: AsyncSession,
    plaid_item: PlaidItem,
    webhook_code: str,
    webhook_data: Dict[str, Any],
):
    """Handle TRANSACTIONS webhook events."""
    if webhook_code in [
        "DEFAULT_UPDATE",
        "INITIAL_UPDATE",
        "HISTORICAL_UPDATE",
        "SYNC_UPDATES_AVAILABLE",
    ]:
        # Debounce: max 1 sync per item per 60 seconds to prevent thundering herd
        sync_lock_key = f"plaid:sync_debounce:{plaid_item.item_id}"
        acquired = await cache_setnx(sync_lock_key, 60)
        if not acquired:
            logger.info(
                "Plaid sync debounced for item %s (code=%s) — already syncing within 60s",
                plaid_item.item_id, webhook_code,
            )
            return

        # New transaction data is available - trigger sync
        logger.info(
            "Transaction data available for item: " f"{plaid_item.item_id} (code={webhook_code})"
        )

        # Check if this is a test user
        result = await db.execute(
            select(User)
            .join(Organization)
            .where(Organization.id == plaid_item.organization_id)
            .limit(1)
        )
        user = result.scalar_one_or_none()
        is_test_user = user and user.email == "test@test.com"

        if is_test_user:
            # Generate mock transaction data for test users
            logger.info("Generating mock transactions for test user")

            # Get accounts for this plaid_item
            accounts_result = await db.execute(
                select(Account).where(Account.plaid_item_id == plaid_item.id)
            )
            accounts = accounts_result.scalars().all()

            # Generate transactions for each account
            all_transactions = []
            end_date = utc_now().date()
            start_date = end_date - timedelta(days=90)

            for account in accounts:
                mock_txns = MockPlaidTransactionGenerator.generate_mock_transactions(
                    account_id=account.external_account_id,
                    start_date=start_date,
                    end_date=end_date,
                    count=30,
                )
                all_transactions.extend(mock_txns)

            # Sync transactions
            sync_service = PlaidTransactionSyncService()
            stats = await sync_service.sync_transactions_for_item(
                db=db,
                plaid_item_id=plaid_item.id,
                transactions_data=all_transactions,
                is_test_mode=True,
            )

            logger.info(f"Synced mock transactions: {stats}")
        else:
            # Real Plaid transaction sync
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

            logger.info(f"Synced real transactions: {stats}")

    elif webhook_code == "TRANSACTIONS_REMOVED":
        # Transactions were removed (e.g., duplicates)
        removed_transaction_ids = webhook_data.get("removed_transactions", [])
        logger.info(f"Transactions removed: {removed_transaction_ids}")

        if removed_transaction_ids:
            sync_service = PlaidTransactionSyncService()
            count = await sync_service.remove_transactions(
                db=db, plaid_item_id=plaid_item.id, removed_transaction_ids=removed_transaction_ids
            )
            logger.info(f"Removed {count} transactions")


async def _handle_auth_webhook(
    db: AsyncSession,
    plaid_item: PlaidItem,
    webhook_code: str,
    webhook_data: Dict[str, Any],
):
    """Handle AUTH webhook events."""
    if webhook_code == "AUTOMATICALLY_VERIFIED":
        logger.info(f"Auth automatically verified for item: {plaid_item.item_id}")
    elif webhook_code == "VERIFICATION_EXPIRED":
        logger.warning(f"Auth verification expired for item: {plaid_item.item_id}")
