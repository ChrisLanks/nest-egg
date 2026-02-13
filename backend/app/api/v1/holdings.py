"""Holdings API endpoints."""

from typing import List
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.holding import Holding
from app.models.account import Account, AccountType
from app.schemas.holding import (
    Holding as HoldingSchema,
    HoldingCreate,
    HoldingUpdate,
    PortfolioSummary,
    HoldingSummary,
)

router = APIRouter()


@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio summary across all investment accounts."""

    # Fetch all holdings for the user's investment accounts
    result = await db.execute(
        select(Holding)
        .join(Account)
        .where(
            Account.organization_id == current_user.organization_id,
            Account.is_active == True,
            Account.account_type.in_([
                AccountType.BROKERAGE,
                AccountType.RETIREMENT_401K,
                AccountType.RETIREMENT_IRA,
                AccountType.RETIREMENT_ROTH,
                AccountType.HSA,
            ])
        )
    )
    holdings = result.scalars().all()

    if not holdings:
        return PortfolioSummary(
            total_value=Decimal('0'),
            total_cost_basis=Decimal('0'),
            total_gain_loss=Decimal('0'),
            total_gain_loss_percent=Decimal('0'),
            holdings_by_ticker=[],
        )

    # Aggregate holdings by ticker
    holdings_by_ticker: dict[str, dict] = {}
    for holding in holdings:
        if holding.ticker not in holdings_by_ticker:
            holdings_by_ticker[holding.ticker] = {
                'ticker': holding.ticker,
                'name': holding.name,
                'total_shares': Decimal('0'),
                'total_cost_basis': Decimal('0'),
                'current_price_per_share': holding.current_price_per_share,
                'price_as_of': holding.price_as_of,
                'asset_type': holding.asset_type,
            }

        holdings_by_ticker[holding.ticker]['total_shares'] += holding.shares
        if holding.total_cost_basis:
            holdings_by_ticker[holding.ticker]['total_cost_basis'] += holding.total_cost_basis

        # Use most recent price
        if holding.price_as_of and (
            not holdings_by_ticker[holding.ticker]['price_as_of'] or
            holding.price_as_of > holdings_by_ticker[holding.ticker]['price_as_of']
        ):
            holdings_by_ticker[holding.ticker]['current_price_per_share'] = holding.current_price_per_share
            holdings_by_ticker[holding.ticker]['price_as_of'] = holding.price_as_of

    # Calculate totals and summaries
    holdings_summaries = []
    total_value = Decimal('0')
    total_cost_basis = Decimal('0')

    # Asset allocation buckets
    stocks_value = Decimal('0')
    bonds_value = Decimal('0')
    etf_value = Decimal('0')
    mutual_funds_value = Decimal('0')
    cash_value = Decimal('0')
    other_value = Decimal('0')

    for ticker_data in holdings_by_ticker.values():
        shares = ticker_data['total_shares']
        price = ticker_data['current_price_per_share']
        cost_basis = ticker_data['total_cost_basis']

        current_total_value = shares * price if price else None
        gain_loss = (current_total_value - cost_basis) if (current_total_value and cost_basis) else None
        gain_loss_percent = ((gain_loss / cost_basis) * 100) if (gain_loss and cost_basis and cost_basis != 0) else None

        summary = HoldingSummary(
            ticker=ticker_data['ticker'],
            name=ticker_data['name'],
            total_shares=shares,
            total_cost_basis=cost_basis,
            current_price_per_share=price,
            current_total_value=current_total_value,
            price_as_of=ticker_data['price_as_of'],
            asset_type=ticker_data['asset_type'],
            gain_loss=gain_loss,
            gain_loss_percent=gain_loss_percent,
        )
        holdings_summaries.append(summary)

        if current_total_value:
            total_value += current_total_value

            # Accumulate by asset type
            asset_type = ticker_data.get('asset_type')
            if asset_type == 'stock':
                stocks_value += current_total_value
            elif asset_type == 'bond':
                bonds_value += current_total_value
            elif asset_type == 'etf':
                etf_value += current_total_value
            elif asset_type == 'mutual_fund':
                mutual_funds_value += current_total_value
            elif asset_type == 'cash':
                cash_value += current_total_value
            else:
                other_value += current_total_value

        if cost_basis:
            total_cost_basis += cost_basis

    total_gain_loss = total_value - total_cost_basis if total_cost_basis else None
    total_gain_loss_percent = ((total_gain_loss / total_cost_basis) * 100) if (total_gain_loss and total_cost_basis and total_cost_basis != 0) else None

    return PortfolioSummary(
        total_value=total_value,
        total_cost_basis=total_cost_basis if total_cost_basis else None,
        total_gain_loss=total_gain_loss,
        total_gain_loss_percent=total_gain_loss_percent,
        holdings_by_ticker=holdings_summaries,
        stocks_value=stocks_value,
        bonds_value=bonds_value,
        etf_value=etf_value,
        mutual_funds_value=mutual_funds_value,
        cash_value=cash_value,
        other_value=other_value,
    )


@router.get("/account/{account_id}", response_model=List[HoldingSchema])
async def get_account_holdings(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all holdings for a specific account."""

    # Verify account belongs to user's organization
    account_result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Fetch holdings
    result = await db.execute(
        select(Holding).where(Holding.account_id == account_id).order_by(Holding.ticker)
    )
    holdings = result.scalars().all()

    return holdings


@router.post("/", response_model=HoldingSchema, status_code=201)
async def create_holding(
    holding_data: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new holding."""

    # Verify account belongs to user's organization
    account_result = await db.execute(
        select(Account).where(
            Account.id == holding_data.account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Verify account is an investment type
    if account.account_type not in [
        AccountType.BROKERAGE,
        AccountType.RETIREMENT_401K,
        AccountType.RETIREMENT_IRA,
        AccountType.RETIREMENT_ROTH,
        AccountType.HSA,
    ]:
        raise HTTPException(status_code=400, detail="Holdings can only be added to investment accounts")

    # Calculate cost basis
    total_cost_basis = None
    if holding_data.cost_basis_per_share:
        total_cost_basis = holding_data.shares * holding_data.cost_basis_per_share

    # Create holding
    holding = Holding(
        account_id=holding_data.account_id,
        organization_id=current_user.organization_id,
        ticker=holding_data.ticker.upper(),  # Normalize to uppercase
        name=holding_data.name,
        shares=holding_data.shares,
        cost_basis_per_share=holding_data.cost_basis_per_share,
        total_cost_basis=total_cost_basis,
        asset_type=holding_data.asset_type,
    )

    db.add(holding)
    await db.commit()
    await db.refresh(holding)

    return holding


@router.patch("/{holding_id}", response_model=HoldingSchema)
async def update_holding(
    holding_id: UUID,
    holding_data: HoldingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a holding."""

    # Fetch holding
    result = await db.execute(
        select(Holding).where(
            Holding.id == holding_id,
            Holding.organization_id == current_user.organization_id,
        )
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    # Update fields
    if holding_data.ticker is not None:
        holding.ticker = holding_data.ticker.upper()
    if holding_data.name is not None:
        holding.name = holding_data.name
    if holding_data.shares is not None:
        holding.shares = holding_data.shares
    if holding_data.cost_basis_per_share is not None:
        holding.cost_basis_per_share = holding_data.cost_basis_per_share
        # Recalculate total cost basis
        holding.total_cost_basis = holding.shares * holding_data.cost_basis_per_share
    if holding_data.current_price_per_share is not None:
        holding.current_price_per_share = holding_data.current_price_per_share
        holding.current_total_value = holding.shares * holding_data.current_price_per_share
        holding.price_as_of = datetime.utcnow()
    if holding_data.asset_type is not None:
        holding.asset_type = holding_data.asset_type

    holding.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(holding)

    return holding


@router.delete("/{holding_id}", status_code=204)
async def delete_holding(
    holding_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a holding."""

    # Fetch holding
    result = await db.execute(
        select(Holding).where(
            Holding.id == holding_id,
            Holding.organization_id == current_user.organization_id,
        )
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    await db.delete(holding)
    await db.commit()

    return None
