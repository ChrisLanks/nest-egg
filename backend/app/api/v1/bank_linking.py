"""Provider-agnostic bank linking API endpoints.

This module provides unified endpoints for linking bank accounts across multiple
providers (Plaid, Teller, MX, etc.) without exposing provider-specific details
to the frontend.
"""

import logging
from typing import List, Dict, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.account import Account, AccountSource
from app.services.plaid_service import PlaidService
from app.services.teller_service import get_teller_service
from app.services.rate_limit_service import rate_limit_service
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Type alias for supported providers
Provider = Literal["plaid", "teller"]


class LinkTokenRequest(BaseModel):
    """Request to create a link token for account linking."""

    provider: Provider


class LinkTokenResponse(BaseModel):
    """Response containing link token."""

    provider: Provider
    link_token: str
    expiration: str


class ExchangeTokenRequest(BaseModel):
    """Request to exchange public/enrollment token for access token."""

    provider: Provider
    public_token: str  # Plaid: public_token, Teller: enrollment_id
    institution_id: str
    institution_name: str
    accounts: List[Dict[str, Any]]  # Provider-specific account metadata


class AccountItem(BaseModel):
    """Account information returned after linking."""

    account_id: str
    name: str
    mask: str | None
    type: str
    subtype: str | None
    current_balance: float


class ExchangeTokenResponse(BaseModel):
    """Response after exchanging token and creating accounts."""

    provider: Provider
    item_id: str  # Plaid: item_id, Teller: enrollment_id
    accounts: List[AccountItem]


@router.post("/link-token", response_model=LinkTokenResponse)
async def create_link_token(
    request: LinkTokenRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a link token for bank account linking.

    Provider-agnostic endpoint that routes to the appropriate service based on
    the provider parameter.

    Rate limited to 10 requests per minute.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=60,
    )

    try:
        if request.provider == "plaid":
            if not settings.PLAID_ENABLED:
                raise HTTPException(status_code=400, detail="Plaid integration is not enabled")

            plaid_service = PlaidService()
            link_token, expiration = await plaid_service.create_link_token(current_user)

            return LinkTokenResponse(
                provider="plaid",
                link_token=link_token,
                expiration=expiration,
            )

        elif request.provider == "teller":
            if not settings.TELLER_ENABLED:
                raise HTTPException(status_code=400, detail="Teller integration is not enabled")

            teller_service = get_teller_service()
            link_url = await teller_service.get_enrollment_url(str(current_user.id))

            # Teller returns a URL, not a token. The frontend should open this URL.
            # For consistency, we return it as link_token with a long expiration.
            return LinkTokenResponse(
                provider="teller",
                link_token=link_url,
                expiration="7d",  # Teller Connect URLs don't expire
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create link token for {request.provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create link token")


@router.post("/exchange-token", response_model=ExchangeTokenResponse)
async def exchange_token(
    request: ExchangeTokenRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange public/enrollment token for access token and create accounts.

    Provider-agnostic endpoint that routes to the appropriate service.

    Rate limited to 5 requests per minute.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=60,
    )

    try:
        if request.provider == "plaid":
            # Use existing Plaid endpoint logic
            from app.api.v1.plaid import exchange_public_token as plaid_exchange
            from app.schemas.plaid import PublicTokenExchangeRequest

            plaid_request = PublicTokenExchangeRequest(
                public_token=request.public_token,
                institution_id=request.institution_id,
                institution_name=request.institution_name,
                accounts=request.accounts,
            )

            plaid_response = await plaid_exchange(
                request=plaid_request,
                http_request=http_request,
                current_user=current_user,
                db=db,
            )

            return ExchangeTokenResponse(
                provider="plaid",
                item_id=plaid_response.item_id,
                accounts=[
                    AccountItem(
                        account_id=acc.account_id,
                        name=acc.name,
                        mask=acc.mask,
                        type=acc.type,
                        subtype=acc.subtype,
                        current_balance=acc.current_balance,
                    )
                    for acc in plaid_response.accounts
                ],
            )

        elif request.provider == "teller":
            teller_service = get_teller_service()

            # Create Teller enrollment
            enrollment = await teller_service.create_enrollment(
                db=db,
                organization_id=current_user.organization_id,
                user_id=current_user.id,
                enrollment_id=request.public_token,  # Teller sends enrollment_id
                access_token=request.public_token,  # In real flow, exchange this
                institution_name=request.institution_name,
            )

            # Sync accounts from Teller
            accounts = await teller_service.sync_accounts(db, enrollment)

            return ExchangeTokenResponse(
                provider="teller",
                item_id=enrollment.enrollment_id,
                accounts=[
                    AccountItem(
                        account_id=acc.external_account_id,
                        name=acc.name,
                        mask=acc.mask,
                        type=acc.account_type.value,
                        subtype=None,
                        current_balance=float(acc.current_balance or 0),
                    )
                    for acc in accounts
                ],
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to exchange token for {request.provider}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to exchange token")


@router.post("/sync-transactions/{account_id}")
async def sync_transactions(
    account_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger transaction sync for an account.

    Provider-agnostic endpoint that automatically determines the provider
    from the account and routes to the appropriate service.

    Rate limited to 5 requests per minute.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=60,
    )

    # Get account and verify ownership
    result = await db.execute(
        select(Account).where(
            Account.id == account_id, Account.organization_id == current_user.organization_id
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        if account.account_source == AccountSource.PLAID:
            # Use Plaid sync logic
            from app.api.v1.plaid import sync_transactions as plaid_sync

            if not account.plaid_item_id:
                raise HTTPException(status_code=400, detail="Account is not linked to a Plaid item")

            return await plaid_sync(
                plaid_item_id=account.plaid_item_id,
                http_request=http_request,
                current_user=current_user,
                db=db,
            )

        elif account.account_source == AccountSource.TELLER:
            # Use Teller sync logic
            teller_service = get_teller_service()

            if not account.teller_enrollment:
                raise HTTPException(
                    status_code=400, detail="Account is not linked to a Teller enrollment"
                )

            transactions = await teller_service.sync_transactions(
                db=db, account=account, days_back=90
            )

            return {
                "success": True,
                "provider": "teller",
                "message": "Transactions synced successfully",
                "stats": {
                    "added": len(transactions),
                },
            }

        elif account.account_source == AccountSource.MANUAL:
            raise HTTPException(
                status_code=400, detail="Manual accounts cannot be synced automatically"
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported account source: {account.account_source.value}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error for account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Sync failed")


@router.get("/providers")
async def list_providers(
    current_user: User = Depends(get_current_user),
):
    """
    List available bank linking providers.

    Returns enabled providers based on server configuration.
    """
    providers = []

    if settings.PLAID_ENABLED:
        providers.append(
            {
                "id": "plaid",
                "name": "Plaid",
                "description": "Connect to 11,000+ banks and financial institutions",
                "coverage": "US, Canada, Europe",
                "features": ["checking", "savings", "credit_cards", "loans", "investments"],
            }
        )

    if settings.TELLER_ENABLED:
        providers.append(
            {
                "id": "teller",
                "name": "Teller",
                "description": "100 free accounts/month, then $1/account",
                "coverage": "US (5,000+ banks)",
                "features": ["checking", "savings", "credit_cards", "loans"],
            }
        )

    return {"providers": providers}
