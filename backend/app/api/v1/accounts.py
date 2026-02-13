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
from app.schemas.account import Account as AccountSchema, AccountSummary, ManualAccountCreate

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

    return account
