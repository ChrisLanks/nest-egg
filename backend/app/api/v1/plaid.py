"""Plaid integration API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.account import Account, PlaidItem, AccountType
from app.schemas.plaid import (
    LinkTokenCreateRequest,
    LinkTokenCreateResponse,
    PublicTokenExchangeRequest,
    PublicTokenExchangeResponse,
    PlaidAccount,
)
from app.services.plaid_service import PlaidService

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
