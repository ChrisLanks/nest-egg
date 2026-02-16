"""Account API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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
    """List all accounts for the current user's organization."""
    # Query accounts directly to respect include_hidden parameter
    if include_hidden:
        # Admin view - include ALL accounts regardless of is_active status
        conditions = [Account.organization_id == current_user.organization_id]
        if user_id:
            await verify_household_member(db, user_id, current_user.organization_id)
            conditions.append(Account.user_id == user_id)

        result = await db.execute(
            select(Account)
            .options(joinedload(Account.plaid_item))
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

    # Construct AccountSummary with PlaidItem sync status
    summaries = []
    for acc in accounts:
        plaid_item = acc.plaid_item if acc.plaid_item_id else None

        summary = AccountSummary(
            id=acc.id,
            user_id=acc.user_id,
            name=acc.name,
            account_type=acc.account_type,
            property_type=acc.property_type,
            institution_name=acc.institution_name,
            mask=acc.mask,
            current_balance=acc.current_balance,
            balance_as_of=acc.balance_as_of,
            is_active=acc.is_active,
            exclude_from_cash_flow=acc.exclude_from_cash_flow,
            plaid_item_hash=acc.plaid_item_hash,
            plaid_item_id=acc.plaid_item_id,
            # Include PlaidItem sync status
            last_synced_at=plaid_item.last_synced_at if plaid_item else None,
            last_error_code=plaid_item.last_error_code if plaid_item else None,
            last_error_message=plaid_item.last_error_message if plaid_item else None,
            needs_reauth=plaid_item.needs_reauth if plaid_item else None,
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


@router.patch("/bulk-visibility")
async def bulk_update_visibility(
    account_ids: List[UUID],
    is_active: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update visibility for multiple accounts. Only updates accounts owned by the current user."""
    # Only allow updating accounts owned by the current user
    result = await db.execute(
        update(Account)
        .where(
            Account.id.in_(account_ids),
            Account.organization_id == current_user.organization_id,
            Account.user_id == current_user.id,  # Must be account owner
        )
        .values(is_active=is_active)
    )
    await db.commit()
    return {"updated_count": result.rowcount}
