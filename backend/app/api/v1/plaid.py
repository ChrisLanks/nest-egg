"""Plaid integration API endpoints."""

from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.account import Account, PlaidItem, AccountType
from app.models.notification import NotificationType, NotificationPriority
from app.schemas.plaid import (
    LinkTokenCreateRequest,
    LinkTokenCreateResponse,
    PublicTokenExchangeRequest,
    PublicTokenExchangeResponse,
    PlaidAccount,
)
from app.services.plaid_service import PlaidService
from app.services.notification_service import notification_service

router = APIRouter()


@router.post("/link-token", response_model=LinkTokenCreateResponse)
async def create_link_token(
    request: LinkTokenCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Plaid Link token for initiating the Plaid Link flow.

    For test@test.com users, returns a dummy token.
    """
    plaid_service = PlaidService()

    try:
        link_token, expiration = await plaid_service.create_link_token(current_user)

        return LinkTokenCreateResponse(
            link_token=link_token,
            expiration=expiration,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create link token: {str(e)}",
        )


@router.post("/exchange-token", response_model=PublicTokenExchangeResponse)
async def exchange_public_token(
    request: PublicTokenExchangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a Plaid public token for an access token and create accounts.

    For test@test.com users, creates accounts with dummy data.
    """
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
        plaid_item = PlaidItem(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            item_id=f"item_{access_token[:16]}",  # Use part of access token as item_id for test
            access_token=access_token.encode(),  # Store as bytes (would be encrypted in production)
            institution_id=request.institution_id,
            institution_name=request.institution_name or "Unknown Institution",
        )
        db.add(plaid_item)
        await db.flush()  # Flush to get the plaid_item.id

        # Create Account records for each Plaid account
        created_accounts: List[PlaidAccount] = []

        for plaid_account in plaid_accounts:
            # Map Plaid account type to our AccountType enum
            account_type = _map_plaid_account_type(
                plaid_account.get("type"),
                plaid_account.get("subtype"),
            )

            account = Account(
                organization_id=current_user.organization_id,
                user_id=current_user.id,
                plaid_item_id=plaid_item.id,
                external_account_id=plaid_account["account_id"],
                name=plaid_account["name"],
                account_type=account_type,
                account_source="plaid",
                institution_name=request.institution_name or "Unknown Institution",
                mask=plaid_account.get("mask"),
                official_name=plaid_account.get("official_name"),
                current_balance=plaid_account.get("current_balance"),
                available_balance=plaid_account.get("available_balance"),
                limit=plaid_account.get("limit"),
                is_manual=False,
                is_active=True,
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

        return PublicTokenExchangeResponse(
            item_id=plaid_item.item_id,
            accounts=created_accounts,
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange token: {str(e)}",
        )


def _map_plaid_account_type(plaid_type: str, plaid_subtype: str) -> AccountType:
    """Map Plaid account type/subtype to our AccountType enum."""
    # Mapping based on Plaid's account types
    # https://plaid.com/docs/api/accounts/#account-type-schema

    if plaid_type == "depository":
        if plaid_subtype == "checking":
            return AccountType.CHECKING
        elif plaid_subtype == "savings":
            return AccountType.SAVINGS
        else:
            return AccountType.CHECKING  # Default for depository

    elif plaid_type == "credit":
        if plaid_subtype == "credit_card":
            return AccountType.CREDIT_CARD
        else:
            return AccountType.LOAN  # Other credit types

    elif plaid_type == "loan":
        if plaid_subtype in ["mortgage", "home_equity"]:
            return AccountType.MORTGAGE
        else:
            return AccountType.LOAN

    elif plaid_type == "investment":
        if plaid_subtype in ["401k", "403b", "457b"]:
            return AccountType.RETIREMENT_401K
        elif plaid_subtype in ["ira", "traditional_ira"]:
            return AccountType.RETIREMENT_IRA
        elif plaid_subtype == "roth":
            return AccountType.RETIREMENT_ROTH
        elif plaid_subtype == "brokerage":
            return AccountType.BROKERAGE
        else:
            return AccountType.BROKERAGE  # Default for investment

    else:
        return AccountType.OTHER  # Fallback


@router.post("/webhook")
async def handle_plaid_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle webhook notifications from Plaid.

    Plaid sends webhooks for various events like:
    - ITEM_ERROR: Item encounters an error
    - PENDING_EXPIRATION: Item access token is about to expire
    - USER_PERMISSION_REVOKED: User revoked permission
    - DEFAULT_UPDATE: General account updates
    """
    try:
        webhook_data: Dict[str, Any] = await request.json()

        webhook_type = webhook_data.get("webhook_type")
        webhook_code = webhook_data.get("webhook_code")
        item_id = webhook_data.get("item_id")

        print(f"📥 Plaid webhook received: {webhook_type} - {webhook_code}")

        # Get PlaidItem to find organization
        result = await db.execute(
            select(PlaidItem).where(PlaidItem.item_id == item_id)
        )
        plaid_item = result.scalar_one_or_none()

        if not plaid_item:
            print(f"⚠️  PlaidItem not found for item_id: {item_id}")
            return {"status": "item_not_found"}

        # Handle different webhook types
        if webhook_type == "ITEM":
            await _handle_item_webhook(db, plaid_item, webhook_code, webhook_data)
        elif webhook_type == "TRANSACTIONS":
            await _handle_transactions_webhook(db, plaid_item, webhook_code, webhook_data)
        elif webhook_type == "AUTH":
            await _handle_auth_webhook(db, plaid_item, webhook_code, webhook_data)

        return {"status": "acknowledged"}

    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
            message=f"Your connection to {plaid_item.institution_name} will expire soon. Please reconnect to continue syncing.",
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
            message=f"Access to {plaid_item.institution_name} has been revoked. Reconnect to continue syncing.",
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
    if webhook_code in ["DEFAULT_UPDATE", "INITIAL_UPDATE", "HISTORICAL_UPDATE"]:
        # New transaction data is available
        # In a full implementation, this would trigger a sync
        print(f"📊 Transaction data available for item: {plaid_item.item_id}")
        # TODO: Trigger transaction sync
    elif webhook_code == "TRANSACTIONS_REMOVED":
        # Transactions were removed (e.g., duplicates)
        removed_transaction_ids = webhook_data.get("removed_transactions", [])
        print(f"🗑️  Transactions removed: {removed_transaction_ids}")
        # TODO: Handle removed transactions


async def _handle_auth_webhook(
    db: AsyncSession,
    plaid_item: PlaidItem,
    webhook_code: str,
    webhook_data: Dict[str, Any],
):
    """Handle AUTH webhook events."""
    if webhook_code == "AUTOMATICALLY_VERIFIED":
        print(f"✅ Auth automatically verified for item: {plaid_item.item_id}")
    elif webhook_code == "VERIFICATION_EXPIRED":
        print(f"⏰ Auth verification expired for item: {plaid_item.item_id}")
