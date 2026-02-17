"""Account API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    get_verified_account,
    verify_household_member,
    get_user_accounts,
    get_all_household_accounts
)
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.holding import Holding
from app.schemas.account import Account as AccountSchema, AccountSummary, ManualAccountCreate, AccountUpdate
from app.services.deduplication_service import DeduplicationService
from app.services.rate_limit_service import rate_limit_service


class BulkVisibilityUpdate(BaseModel):
    """Request model for bulk visibility updates."""
    account_ids: List[UUID]
    is_active: bool

router = APIRouter()

# Initialize deduplication service
deduplication_service = DeduplicationService()


@router.get("/", response_model=List[AccountSummary])
async def list_accounts(
    include_hidden: bool = Query(False, description="Include hidden accounts (admin view)"),
    user_id: Optional[UUID] = Query(None, description="Filter by user. None = combined household view"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all accounts for the current user's organization (provider-agnostic)."""
    # Query accounts directly to respect include_hidden parameter
    if include_hidden:
        # Admin view - include ALL accounts regardless of is_active status
        conditions = [Account.organization_id == current_user.organization_id]
        if user_id:
            await verify_household_member(db, user_id, current_user.organization_id)
            conditions.append(Account.user_id == user_id)

        result = await db.execute(
            select(Account)
            .options(
                joinedload(Account.plaid_item),
                joinedload(Account.teller_enrollment)
            )
            .where(*conditions)
        )
        accounts = result.unique().scalars().all()
    else:
        # Normal view - use existing dependencies that filter by is_active
        if user_id:
            await verify_household_member(db, user_id, current_user.organization_id)
            accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        else:
            accounts = await get_all_household_accounts(db, current_user.organization_id)

    # Sort by name
    accounts = sorted(accounts, key=lambda a: a.name)

    # Construct AccountSummary with provider-agnostic sync status
    summaries = []
    for acc in accounts:
        # Determine which provider to use for sync status
        provider_item_id = None
        last_synced_at = None
        last_error_code = None
        last_error_message = None
        needs_reauth = None

        if acc.account_source.value == "plaid" and acc.plaid_item:
            provider_item_id = acc.plaid_item_id
            last_synced_at = acc.plaid_item.last_synced_at
            last_error_code = acc.plaid_item.last_error_code
            last_error_message = acc.plaid_item.last_error_message
            needs_reauth = acc.plaid_item.needs_reauth
        elif acc.account_source.value == "teller" and acc.teller_enrollment:
            provider_item_id = acc.teller_enrollment_id
            last_synced_at = acc.teller_enrollment.last_synced_at
            last_error_code = acc.teller_enrollment.last_error_code
            last_error_message = acc.teller_enrollment.last_error_message
            needs_reauth = False  # Teller doesn't use reauth concept

        summary = AccountSummary(
            id=acc.id,
            user_id=acc.user_id,
            name=acc.name,
            account_type=acc.account_type,
            account_source=acc.account_source,
            property_type=acc.property_type,
            institution_name=acc.institution_name,
            mask=acc.mask,
            current_balance=acc.current_balance,
            balance_as_of=acc.balance_as_of,
            is_active=acc.is_active,
            exclude_from_cash_flow=acc.exclude_from_cash_flow,
            plaid_item_hash=acc.plaid_item_hash,
            # Provider-agnostic sync status
            provider_item_id=provider_item_id,
            last_synced_at=last_synced_at,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
            needs_reauth=needs_reauth,
        )
        summaries.append(summary)

    return summaries


@router.get("/{account_id}", response_model=AccountSchema)
async def get_account(
    account: Account = Depends(get_verified_account),
):
    """Get a specific account."""
    return account


@router.post("/manual", response_model=AccountSchema)
async def create_manual_account(
    account_data: ManualAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual account."""
    # Generate hash for deduplication across household members
    plaid_item_hash = deduplication_service.calculate_manual_account_hash(
        account_type=account_data.account_type,
        institution_name=account_data.institution,
        mask=account_data.account_number_last4,
        name=account_data.name
    )

    # Determine if account should be excluded from cash flow by default
    # Loans and mortgages are excluded to prevent double-counting (payment from checking + loan balance decrease)
    exclude_from_cash_flow = account_data.account_type in [
        AccountType.MORTGAGE,
        AccountType.LOAN,
        AccountType.STUDENT_LOAN,
        AccountType.CREDIT_CARD,
    ]

    # Create the account
    account = Account(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        name=account_data.name,
        account_type=account_data.account_type,
        account_source=account_data.account_source,
        institution_name=account_data.institution,
        mask=account_data.account_number_last4,
        current_balance=account_data.balance,
        plaid_item_hash=plaid_item_hash,
        is_manual=True,
        is_active=True,
        exclude_from_cash_flow=exclude_from_cash_flow,
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    # Create holdings if provided (for investment accounts)
    if account_data.holdings:
        for holding_data in account_data.holdings:
            # Calculate cost basis (use current price as cost basis)
            cost_basis_per_share = holding_data.price_per_share
            total_cost_basis = holding_data.shares * cost_basis_per_share

            holding = Holding(
                account_id=account.id,
                organization_id=current_user.organization_id,
                ticker=holding_data.ticker.upper(),
                shares=holding_data.shares,
                cost_basis_per_share=cost_basis_per_share,
                total_cost_basis=total_cost_basis,
                current_price_per_share=holding_data.price_per_share,
                current_total_value=holding_data.shares * holding_data.price_per_share,
            )
            db.add(holding)

        await db.commit()

    return account


@router.patch("/bulk-visibility")
async def bulk_update_visibility(
    request: BulkVisibilityUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update visibility for multiple accounts.
    Rate limited to 30 requests per minute.
    Only updates accounts owned by the current user.
    """
    # Rate limit: 30 bulk update requests per minute per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=30,
        window_seconds=60,
    )

    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[bulk-visibility] Request: account_ids={request.account_ids}, is_active={request.is_active}, user_id={current_user.id}, org_id={current_user.organization_id}")

    # Check which accounts exist and are owned by the user
    check_result = await db.execute(
        select(Account.id, Account.user_id, Account.organization_id, Account.is_active)
        .where(Account.id.in_(request.account_ids))
    )
    existing_accounts = check_result.all()
    logger.info(f"[bulk-visibility] Found {len(existing_accounts)} accounts: {existing_accounts}")

    # Only allow updating accounts owned by the current user
    result = await db.execute(
        update(Account)
        .where(
            Account.id.in_(request.account_ids),
            Account.organization_id == current_user.organization_id,
            Account.user_id == current_user.id,  # Must be account owner
        )
        .values(is_active=request.is_active)
    )
    await db.commit()

    logger.info(f"[bulk-visibility] Updated {result.rowcount} accounts")

    return {"updated_count": result.rowcount}


@router.patch("/{account_id}", response_model=AccountSchema)
async def update_account(
    account_data: AccountUpdate,
    account: Account = Depends(get_verified_account),
    db: AsyncSession = Depends(get_db),
):
    """Update account details."""
    # Update fields
    if account_data.name is not None:
        account.name = account_data.name
    if account_data.is_active is not None:
        account.is_active = account_data.is_active
    if account_data.current_balance is not None:
        account.current_balance = account_data.current_balance
    if account_data.mask is not None:
        account.mask = account_data.mask
    if account_data.exclude_from_cash_flow is not None:
        account.exclude_from_cash_flow = account_data.exclude_from_cash_flow

    await db.commit()
    await db.refresh(account)

    return account


@router.post("/bulk-delete")
async def bulk_delete_accounts(
    account_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple accounts at once. Only deletes accounts owned by the current user."""
    # Only allow deletion of accounts owned by the current user
    result = await db.execute(
        delete(Account).where(
            Account.id.in_(account_ids),
            Account.organization_id == current_user.organization_id,
            Account.user_id == current_user.id,  # Must be account owner
        )
    )
    await db.commit()
    return {"deleted_count": result.rowcount}
