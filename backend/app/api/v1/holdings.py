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
    CategoryBreakdown,
    GeographicBreakdown,
    TreemapNode,
)

router = APIRouter()


@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio summary across all investment accounts."""

    # Fetch all accounts for treemap (including property/vehicles)
    accounts_result = await db.execute(
        select(Account)
        .where(
            Account.organization_id == current_user.organization_id,
            Account.is_active == True,
        )
    )
    accounts = accounts_result.scalars().all()

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
                AccountType.CRYPTO,  # Include crypto accounts
            ])
        )
        .options(selectinload(Holding.account))
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

    # Calculate category breakdown (Retirement vs Taxable)
    retirement_types = [
        AccountType.RETIREMENT_401K,
        AccountType.RETIREMENT_IRA,
        AccountType.RETIREMENT_ROTH,
        AccountType.HSA,
    ]

    retirement_value = Decimal('0')
    taxable_value = Decimal('0')

    # Group holdings by account type
    holdings_by_account: dict[UUID, list] = {}
    for holding in holdings:
        if holding.account_id not in holdings_by_account:
            holdings_by_account[holding.account_id] = []
        holdings_by_account[holding.account_id].append(holding)

    for account in accounts:
        if account.account_type in retirement_types:
            # Sum holdings in this retirement account
            if account.id in holdings_by_account:
                for holding in holdings_by_account[account.id]:
                    if holding.current_total_value:
                        retirement_value += holding.current_total_value
        elif account.account_type == AccountType.BROKERAGE:
            # Sum holdings in taxable brokerage
            if account.id in holdings_by_account:
                for holding in holdings_by_account[account.id]:
                    if holding.current_total_value:
                        taxable_value += holding.current_total_value

    category_breakdown = CategoryBreakdown(
        retirement_value=retirement_value,
        retirement_percent=(retirement_value / total_value * 100) if total_value > 0 else None,
        taxable_value=taxable_value,
        taxable_percent=(taxable_value / total_value * 100) if total_value > 0 else None,
        other_value=total_value - retirement_value - taxable_value,
        other_percent=((total_value - retirement_value - taxable_value) / total_value * 100) if total_value > 0 else None,
    )

    # Calculate geographic breakdown (simple heuristic)
    international_tickers = {
        'VXUS', 'VEU', 'VWO', 'VGTSX', 'VTIAX', 'VTMGX', 'VEA', 'IEMG', 'IXUS',
        'SCHF', 'EFA', 'IEFA', 'VFWAX', 'VFWIX', 'VTSNX', 'VEMAX', 'VIMSX'
    }

    domestic_value = Decimal('0')
    international_value = Decimal('0')
    unknown_value = Decimal('0')

    for summary in holdings_summaries:
        if summary.current_total_value:
            if summary.ticker.upper() in international_tickers:
                international_value += summary.current_total_value
            elif summary.asset_type in ['stock', 'etf', 'mutual_fund']:
                # Assume domestic for US stocks/ETFs not in international list
                domestic_value += summary.current_total_value
            else:
                unknown_value += summary.current_total_value

    geographic_breakdown = GeographicBreakdown(
        domestic_value=domestic_value,
        domestic_percent=(domestic_value / total_value * 100) if total_value > 0 else None,
        international_value=international_value,
        international_percent=(international_value / total_value * 100) if total_value > 0 else None,
        unknown_value=unknown_value,
        unknown_percent=(unknown_value / total_value * 100) if total_value > 0 else None,
    )

    # Generate treemap data with hierarchical structure
    # Top level: Account Categories (Retirement, Taxable, Property, Vehicles)
    treemap_children = []

    # Add Retirement category
    if retirement_value > 0:
        retirement_children = []

        # Group retirement holdings by asset type
        ret_stocks = Decimal('0')
        ret_etfs = Decimal('0')
        ret_mutual_funds = Decimal('0')
        ret_other = Decimal('0')

        ret_stocks_holdings = []
        ret_etfs_holdings = []
        ret_mutual_funds_holdings = []
        ret_other_holdings = []

        for account in accounts:
            if account.account_type in retirement_types and account.id in holdings_by_account:
                for holding in holdings_by_account[account.id]:
                    if holding.current_total_value:
                        holding_node = TreemapNode(
                            name=holding.ticker,
                            value=holding.current_total_value,
                            percent=(holding.current_total_value / retirement_value * 100),
                        )

                        if holding.asset_type == 'stock':
                            ret_stocks += holding.current_total_value
                            ret_stocks_holdings.append(holding_node)
                        elif holding.asset_type == 'etf':
                            ret_etfs += holding.current_total_value
                            ret_etfs_holdings.append(holding_node)
                        elif holding.asset_type == 'mutual_fund':
                            ret_mutual_funds += holding.current_total_value
                            ret_mutual_funds_holdings.append(holding_node)
                        else:
                            ret_other += holding.current_total_value
                            ret_other_holdings.append(holding_node)

        if ret_stocks > 0:
            retirement_children.append(TreemapNode(
                name="Stocks",
                value=ret_stocks,
                percent=(ret_stocks / retirement_value * 100),
                children=ret_stocks_holdings,
                color="#4299E1"
            ))
        if ret_etfs > 0:
            retirement_children.append(TreemapNode(
                name="ETFs",
                value=ret_etfs,
                percent=(ret_etfs / retirement_value * 100),
                children=ret_etfs_holdings,
                color="#319795"
            ))
        if ret_mutual_funds > 0:
            retirement_children.append(TreemapNode(
                name="Mutual Funds",
                value=ret_mutual_funds,
                percent=(ret_mutual_funds / retirement_value * 100),
                children=ret_mutual_funds_holdings,
                color="#D69E2E"
            ))
        if ret_other > 0:
            retirement_children.append(TreemapNode(
                name="Other",
                value=ret_other,
                percent=(ret_other / retirement_value * 100),
                children=ret_other_holdings,
                color="#A0AEC0"
            ))

        treemap_children.append(TreemapNode(
            name="Retirement",
            value=retirement_value,
            percent=(retirement_value / total_value * 100) if total_value > 0 else Decimal('0'),
            children=retirement_children,
            color="#805AD5"
        ))

    # Add Taxable category
    if taxable_value > 0:
        taxable_children = []

        # Group taxable holdings by asset type
        tax_stocks = Decimal('0')
        tax_etfs = Decimal('0')
        tax_mutual_funds = Decimal('0')
        tax_other = Decimal('0')

        tax_stocks_holdings = []
        tax_etfs_holdings = []
        tax_mutual_funds_holdings = []
        tax_other_holdings = []

        for account in accounts:
            if account.account_type == AccountType.BROKERAGE and account.id in holdings_by_account:
                for holding in holdings_by_account[account.id]:
                    if holding.current_total_value:
                        holding_node = TreemapNode(
                            name=holding.ticker,
                            value=holding.current_total_value,
                            percent=(holding.current_total_value / taxable_value * 100),
                        )

                        if holding.asset_type == 'stock':
                            tax_stocks += holding.current_total_value
                            tax_stocks_holdings.append(holding_node)
                        elif holding.asset_type == 'etf':
                            tax_etfs += holding.current_total_value
                            tax_etfs_holdings.append(holding_node)
                        elif holding.asset_type == 'mutual_fund':
                            tax_mutual_funds += holding.current_total_value
                            tax_mutual_funds_holdings.append(holding_node)
                        else:
                            tax_other += holding.current_total_value
                            tax_other_holdings.append(holding_node)

        if tax_stocks > 0:
            taxable_children.append(TreemapNode(
                name="Stocks",
                value=tax_stocks,
                percent=(tax_stocks / taxable_value * 100),
                children=tax_stocks_holdings,
                color="#4299E1"
            ))
        if tax_etfs > 0:
            taxable_children.append(TreemapNode(
                name="ETFs",
                value=tax_etfs,
                percent=(tax_etfs / taxable_value * 100),
                children=tax_etfs_holdings,
                color="#319795"
            ))
        if tax_mutual_funds > 0:
            taxable_children.append(TreemapNode(
                name="Mutual Funds",
                value=tax_mutual_funds,
                percent=(tax_mutual_funds / taxable_value * 100),
                children=tax_mutual_funds_holdings,
                color="#D69E2E"
            ))
        if tax_other > 0:
            taxable_children.append(TreemapNode(
                name="Other",
                value=tax_other,
                percent=(tax_other / taxable_value * 100),
                children=tax_other_holdings,
                color="#A0AEC0"
            ))

        treemap_children.append(TreemapNode(
            name="Taxable",
            value=taxable_value,
            percent=(taxable_value / total_value * 100) if total_value > 0 else Decimal('0'),
            children=taxable_children,
            color="#3182CE"
        ))

    # Add Property accounts
    property_value = Decimal('0')
    property_children = []
    for account in accounts:
        if account.account_type == AccountType.PROPERTY and account.current_balance:
            property_value += account.current_balance
            property_children.append(TreemapNode(
                name=account.name,
                value=account.current_balance,
                percent=(account.current_balance / property_value * 100) if property_value > 0 else Decimal('0'),
            ))

    if property_value > 0:
        # Update total to include property
        total_with_property = total_value + property_value
        treemap_children.append(TreemapNode(
            name="Property",
            value=property_value,
            percent=(property_value / total_with_property * 100),
            children=property_children if property_children else None,
            color="#ED8936"
        ))
        # Update total_value for percentage calculations
        total_value = total_with_property

    # Add Vehicle accounts
    vehicle_value = Decimal('0')
    vehicle_children = []
    for account in accounts:
        if account.account_type == AccountType.VEHICLE and account.current_balance:
            vehicle_value += account.current_balance
            vehicle_children.append(TreemapNode(
                name=account.name,
                value=account.current_balance,
                percent=(account.current_balance / vehicle_value * 100) if vehicle_value > 0 else Decimal('0'),
            ))

    if vehicle_value > 0:
        total_with_vehicles = total_value + vehicle_value
        treemap_children.append(TreemapNode(
            name="Vehicles",
            value=vehicle_value,
            percent=(vehicle_value / total_with_vehicles * 100),
            children=vehicle_children if vehicle_children else None,
            color="#38B2AC"
        ))
        total_value = total_with_vehicles

    # Add Crypto accounts with holdings
    crypto_value = Decimal('0')
    crypto_holdings_list = []

    # First pass: calculate total crypto value
    for account in accounts:
        if account.account_type == AccountType.CRYPTO and account.id in holdings_by_account:
            for holding in holdings_by_account[account.id]:
                if holding.current_total_value:
                    crypto_value += holding.current_total_value
                    crypto_holdings_list.append(holding)

    # Second pass: create nodes with correct percentages
    crypto_children = []
    if crypto_value > 0:
        for holding in crypto_holdings_list:
            crypto_children.append(TreemapNode(
                name=holding.ticker,
                value=holding.current_total_value,
                percent=(holding.current_total_value / crypto_value * 100),
            ))

        total_with_crypto = total_value + crypto_value
        treemap_children.append(TreemapNode(
            name="Crypto",
            value=crypto_value,
            percent=(crypto_value / total_with_crypto * 100),
            children=crypto_children,
            color="#9F7AEA"
        ))
        total_value = total_with_crypto

    # Recalculate percentages for all top-level nodes
    for child in treemap_children:
        child.percent = (child.value / total_value * 100) if total_value > 0 else Decimal('0')

    # Create root treemap node
    treemap_data = TreemapNode(
        name="Portfolio",
        value=total_value,
        percent=Decimal('100'),
        children=treemap_children,
    ) if treemap_children else None

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
        category_breakdown=category_breakdown,
        geographic_breakdown=geographic_breakdown,
        treemap_data=treemap_data,
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
