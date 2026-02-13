"""Account API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.holding import Holding
from app.schemas.account import Account as AccountSchema, AccountSummary, ManualAccountCreate, AccountUpdate

router = APIRouter()


@router.get("/", response_model=List[AccountSummary])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all accounts for the current user's organization."""
    result = await db.execute(
        select(Account)
        .where(
            Account.organization_id == current_user.organization_id,
            Account.is_active == True,
        )
        .order_by(Account.name)
    )
    accounts = result.scalars().all()
    return accounts


@router.get("/{account_id}", response_model=AccountSchema)
async def get_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific account."""
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return account


@router.post("/manual", response_model=AccountSchema)
async def create_manual_account(
    account_data: ManualAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual account."""
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
        is_manual=True,
        is_active=True,
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
    account_id: UUID,
    account_data: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update account details."""
    # Get the account
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Update fields
    if account_data.name is not None:
        account.name = account_data.name
    if account_data.is_active is not None:
        account.is_active = account_data.is_active
    if account_data.current_balance is not None:
        account.current_balance = account_data.current_balance
    if account_data.mask is not None:
        account.mask = account_data.mask

    await db.commit()
    await db.refresh(account)

    return account
