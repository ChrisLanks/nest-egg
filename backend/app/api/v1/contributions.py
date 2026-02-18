"""Contribution API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_verified_account
from app.models.user import User
from app.models.account import Account
from app.models.contribution import AccountContribution
from app.schemas.contribution import Contribution, ContributionCreate, ContributionUpdate

router = APIRouter()


@router.post(
    "/accounts/{account_id}/contributions",
    response_model=Contribution,
    status_code=status.HTTP_201_CREATED,
)
async def create_contribution(
    contribution_data: ContributionCreate,
    account: Account = Depends(get_verified_account),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new recurring contribution for an account."""
    # Create contribution
    contribution = AccountContribution(
        organization_id=current_user.organization_id,
        account_id=account.id,
        **contribution_data.model_dump(),
    )

    db.add(contribution)
    await db.commit()
    await db.refresh(contribution)

    return contribution


@router.get("/accounts/{account_id}/contributions", response_model=List[Contribution])
async def list_contributions(
    include_inactive: bool = False,
    account: Account = Depends(get_verified_account),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all contributions for an account."""
    # Build query
    query = select(AccountContribution).where(
        AccountContribution.account_id == account.id,
        AccountContribution.organization_id == current_user.organization_id,
    )

    if not include_inactive:
        query = query.where(AccountContribution.is_active)

    query = query.order_by(AccountContribution.created_at.desc())

    result = await db.execute(query)
    contributions = result.scalars().all()

    return contributions


@router.get("/contributions/{contribution_id}", response_model=Contribution)
async def get_contribution(
    contribution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific contribution by ID."""
    result = await db.execute(
        select(AccountContribution).where(
            AccountContribution.id == contribution_id,
            AccountContribution.organization_id == current_user.organization_id,
        )
    )
    contribution = result.scalar_one_or_none()

    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")

    return contribution


@router.patch("/contributions/{contribution_id}", response_model=Contribution)
async def update_contribution(
    contribution_id: UUID,
    contribution_update: ContributionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a contribution."""
    # Get contribution
    result = await db.execute(
        select(AccountContribution).where(
            AccountContribution.id == contribution_id,
            AccountContribution.organization_id == current_user.organization_id,
        )
    )
    contribution = result.scalar_one_or_none()

    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")

    # Update fields
    update_data = contribution_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contribution, field, value)

    await db.commit()
    await db.refresh(contribution)

    return contribution


@router.delete("/contributions/{contribution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contribution(
    contribution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a contribution."""
    result = await db.execute(
        select(AccountContribution).where(
            AccountContribution.id == contribution_id,
            AccountContribution.organization_id == current_user.organization_id,
        )
    )
    contribution = result.scalar_one_or_none()

    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")

    await db.delete(contribution)
    await db.commit()

    return None
