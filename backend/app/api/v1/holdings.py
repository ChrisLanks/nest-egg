"""Holdings API endpoints."""

import asyncio as _asyncio
import logging
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import delete_pattern as cache_delete_pattern
from app.core.cache import get as cache_get
from app.core.cache import setex as cache_setex
from app.core.database import AsyncSessionLocal, get_db
from app.dependencies import (
    get_all_household_accounts,
    get_current_user,
    get_user_accounts,
    get_verified_account,
    verify_household_member,
)
from app.models.account import Account, AccountType, TaxTreatment
from app.models.holding import Holding
from app.models.user import User
from app.schemas.holding import (
    AccountHoldings,
    CategoryBreakdown,
    FeeAnalysisResponse,
    FeeDragProjection,
    FundOverlapResponse,
    GeographicBreakdown,
    HighFeeHolding,
    HoldingCreate,
    HoldingSummary,
    HoldingUpdate,
    LowCostAlternative,
    OverlapGroup,
    PortfolioSummary,
    SectorBreakdown,
    SnapshotResponse,
    StyleBoxItem,
    TreemapNode,
)
from app.schemas.holding import (
    Holding as HoldingSchema,
)
from app.schemas.rmd import AccountRMD, RMDSummary
from app.services.deduplication_service import deduplication_service
from app.services.input_sanitization_service import input_sanitization_service
from app.services.market_data import get_market_data_provider
from app.services.snapshot_service import snapshot_service
from app.utils.account_type_groups import (
    ALL_RETIREMENT_TYPES,
    CASH_ACCOUNT_TYPES,
    INVESTMENT_ACCOUNT_TYPES,
    RMD_ACCOUNT_TYPES,
    ROTH_CONVERSION_ELIGIBLE_TYPES,
)
from app.utils.date_validation import validate_date_range
from app.utils.datetime_utils import utc_now
from app.utils.rmd_calculator import (
    calculate_age,
    calculate_rmd,
    calculate_rmd_penalty,
    get_rmd_deadline,
    requires_rmd,
)

router = APIRouter()


@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    detail_level: str = Query(
        "full",
        description="'summary' returns totals + holdings_by_ticker only (faster). "
        "'full' includes breakdowns, treemap, and per-account detail.",
        pattern="^(summary|full)$",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio summary for a specific user or combined household.

    If user_id is provided, shows only that user's accounts (owned + shared).
    If user_id is None (default), shows all household accounts with deduplication.
    """
    logger = logging.getLogger(__name__)

    logger.info(f"Portfolio request from user {current_user.id}, filter user_id={user_id}")

    # Check cache
    cache_key = (
        f"portfolio:summary:{current_user.organization_id}"
        f":{user_id or 'household'}:{detail_level}"
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    # Get accounts based on filter
    if user_id:
        # Verify user is in same household
        await verify_household_member(db, user_id, current_user.organization_id)

        # Get accounts for specific user (owned + shared)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        # Get all household accounts
        accounts = await get_all_household_accounts(db, current_user.organization_id)

        # Deduplicate accounts (remove duplicates where same real account added by multiple users)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    # Filter accounts for investment accounts only
    investment_account_ids = [
        acc.id for acc in accounts if acc.account_type in INVESTMENT_ACCOUNT_TYPES
    ]

    # Fetch holdings for the filtered investment accounts (capped at 10 000 rows as
    # a safety net; no real portfolio should ever approach this limit)
    if investment_account_ids:
        result = await db.execute(
            select(Holding)
            .join(Account)
            .where(Holding.account_id.in_(investment_account_ids))
            .options(selectinload(Holding.account))
            .limit(10000)
        )
        holdings = result.scalars().all()
    else:
        holdings = []

    # Don't return early if no holdings - accounts may still have balances without detailed holdings
    # (e.g., investment accounts that haven't been synced yet or don't have holdings data)

    # Aggregate holdings by ticker using SQL GROUP BY
    if investment_account_ids:
        agg_query = (
            select(
                Holding.ticker,
                func.max(Holding.name).label("name"),
                func.sum(Holding.shares).label("total_shares"),
                func.coalesce(func.sum(Holding.total_cost_basis), Decimal("0")).label(
                    "total_cost_basis"
                ),
                func.max(Holding.asset_type).label("asset_type"),
                func.max(Holding.sector).label("sector"),
                func.max(Holding.industry).label("industry"),
                func.max(Holding.country).label("country"),
                func.max(Holding.expense_ratio).label("expense_ratio"),
                # Use the price from the most recently updated holding
                func.max(Holding.current_price_per_share).label("current_price_per_share"),
                func.max(Holding.price_as_of).label("price_as_of"),
            )
            .where(Holding.account_id.in_(investment_account_ids))
            .group_by(Holding.ticker)
        )
        agg_result = await db.execute(agg_query)
        aggregated_rows = agg_result.all()
    else:
        aggregated_rows = []

    # Calculate totals and summaries
    holdings_summaries = []
    total_value = Decimal("0")
    total_cost_basis = Decimal("0")
    total_annual_fees = Decimal("0")

    # Asset allocation buckets
    stocks_value = Decimal("0")
    bonds_value = Decimal("0")
    etf_value = Decimal("0")
    mutual_funds_value = Decimal("0")
    cash_value = Decimal("0")
    other_value = Decimal("0")

    for row in aggregated_rows:
        shares = row.total_shares
        price = row.current_price_per_share
        cost_basis = row.total_cost_basis

        current_total_value = shares * price if price else None
        gain_loss = (
            (current_total_value - cost_basis) if (current_total_value and cost_basis) else None
        )
        gain_loss_percent = (
            ((gain_loss / cost_basis) * 100)
            if (gain_loss and cost_basis and cost_basis != 0)
            else None
        )

        # Calculate annual fee if expense ratio exists
        expense_ratio = row.expense_ratio
        annual_fee = (
            (current_total_value * expense_ratio)
            if (current_total_value and expense_ratio)
            else None
        )

        summary = HoldingSummary(
            ticker=row.ticker,
            name=row.name,
            total_shares=shares,
            total_cost_basis=cost_basis,
            current_price_per_share=price,
            current_total_value=current_total_value,
            price_as_of=row.price_as_of,
            asset_type=row.asset_type,
            sector=row.sector,
            industry=row.industry,
            country=row.country,
            expense_ratio=expense_ratio,
            gain_loss=gain_loss,
            gain_loss_percent=gain_loss_percent,
            annual_fee=annual_fee,
        )
        holdings_summaries.append(summary)

        if current_total_value:
            total_value += current_total_value

            # Accumulate annual fees
            if annual_fee:
                total_annual_fees += annual_fee

            # Accumulate by asset type
            asset_type = row.asset_type
            if asset_type == "stock":
                stocks_value += current_total_value
            elif asset_type == "bond":
                bonds_value += current_total_value
            elif asset_type == "etf":
                etf_value += current_total_value
            elif asset_type == "mutual_fund":
                mutual_funds_value += current_total_value
            elif asset_type == "cash":
                cash_value += current_total_value
            else:
                other_value += current_total_value

        if cost_basis:
            total_cost_basis += cost_basis

    total_gain_loss = total_value - total_cost_basis if total_cost_basis else None
    total_gain_loss_percent = (
        ((total_gain_loss / total_cost_basis) * 100)
        if (total_gain_loss and total_cost_basis and total_cost_basis != 0)
        else None
    )

    # Fast path: summary mode skips heavy breakdowns (treemap, sector, geographic, per-account)
    if detail_level == "summary":
        summary = PortfolioSummary(
            total_value=total_value,
            total_cost_basis=total_cost_basis if total_cost_basis else None,
            total_gain_loss=total_gain_loss,
            total_gain_loss_percent=total_gain_loss_percent,
            holdings_by_ticker=holdings_summaries,
            holdings_by_account=[],
            stocks_value=stocks_value,
            bonds_value=bonds_value,
            etf_value=etf_value,
            mutual_funds_value=mutual_funds_value,
            cash_value=cash_value,
            other_value=other_value,
            category_breakdown=None,
            geographic_breakdown=None,
            treemap_data=None,
            sector_breakdown=None,
            total_annual_fees=total_annual_fees if total_annual_fees > 0 else None,
        )
        await cache_setex(cache_key, 300, summary.model_dump(mode="json"))
        return summary

    # Aggregate sector breakdown from holdings
    sector_dict: dict[str, dict] = {}
    for holding in holdings:
        if holding.current_total_value and holding.sector:
            sector = holding.sector
            if sector not in sector_dict:
                sector_dict[sector] = {"value": Decimal("0"), "count": 0}
            sector_dict[sector]["value"] += holding.current_total_value
            sector_dict[sector]["count"] += 1

    # Convert to SectorBreakdown objects and calculate percentages
    sector_breakdown = []
    if sector_dict and total_value > 0:
        for sector, data in sector_dict.items():
            percentage = data["value"] / total_value * 100
            sector_breakdown.append(
                SectorBreakdown(
                    sector=sector,
                    value=data["value"],
                    count=data["count"],
                    percentage=percentage,
                )
            )
        # Sort by value descending
        sector_breakdown.sort(key=lambda x: x.value, reverse=True)
    else:
        sector_breakdown = None

    # Calculate category breakdown (Retirement vs Taxable) using tax_treatment field
    retirement_value = Decimal("0")
    taxable_value = Decimal("0")

    # Group holdings by account
    holdings_by_account: dict[UUID, list] = {}
    for holding in holdings:
        if holding.account_id not in holdings_by_account:
            holdings_by_account[holding.account_id] = []
        holdings_by_account[holding.account_id].append(holding)

    for account in accounts:
        acct_value = Decimal("0")
        if account.id in holdings_by_account:
            for holding in holdings_by_account[account.id]:
                if holding.current_total_value:
                    acct_value += holding.current_total_value

        if acct_value == 0:
            continue

        # Use tax_treatment to classify: PRE_TAX/ROTH/TAX_FREE → retirement, TAXABLE → taxable
        if account.tax_treatment in (
            TaxTreatment.PRE_TAX,
            TaxTreatment.ROTH,
            TaxTreatment.TAX_FREE,
        ):
            retirement_value += acct_value
        elif account.tax_treatment == TaxTreatment.TAXABLE:
            taxable_value += acct_value
        else:
            # Fallback for accounts without tax_treatment set — use account_type
            retirement_types = ALL_RETIREMENT_TYPES
            if account.account_type in retirement_types:
                retirement_value += acct_value
            elif account.account_type == AccountType.BROKERAGE:
                taxable_value += acct_value

    category_breakdown = CategoryBreakdown(
        retirement_value=retirement_value,
        retirement_percent=(retirement_value / total_value * 100) if total_value > 0 else None,
        taxable_value=taxable_value,
        taxable_percent=(taxable_value / total_value * 100) if total_value > 0 else None,
        other_value=total_value - retirement_value - taxable_value,
        other_percent=(
            ((total_value - retirement_value - taxable_value) / total_value * 100)
            if total_value > 0
            else None
        ),
    )

    # Calculate geographic breakdown (simple heuristic)
    international_tickers = {
        "VXUS",
        "VEU",
        "VWO",
        "VGTSX",
        "VTIAX",
        "VTMGX",
        "VEA",
        "IEMG",
        "IXUS",
        "SCHF",
        "EFA",
        "IEFA",
        "VFWAX",
        "VFWIX",
        "VTSNX",
        "VEMAX",
        "VIMSX",
    }

    domestic_value = Decimal("0")
    international_value = Decimal("0")
    unknown_value = Decimal("0")

    for summary in holdings_summaries:
        if summary.current_total_value:
            asset_class = (
                (summary.asset_class or "").lower() if hasattr(summary, "asset_class") else ""
            )
            country = (summary.country or "") if hasattr(summary, "country") else ""

            # Check asset_class first, then fallback to hardcoded list or country
            if (
                asset_class == "international"
                or summary.ticker.upper() in international_tickers
                or (country and country not in ["USA", "US", "United States", ""])
            ):
                international_value += summary.current_total_value
            elif summary.asset_type in ["stock", "etf", "mutual_fund"]:
                # Assume domestic for US stocks/ETFs not in international list
                domestic_value += summary.current_total_value
            else:
                unknown_value += summary.current_total_value

    geographic_breakdown = GeographicBreakdown(
        domestic_value=domestic_value,
        domestic_percent=(domestic_value / total_value * 100) if total_value > 0 else None,
        international_value=international_value,
        international_percent=(
            (international_value / total_value * 100) if total_value > 0 else None
        ),
        unknown_value=unknown_value,
        unknown_percent=(unknown_value / total_value * 100) if total_value > 0 else None,
    )

    # Generate treemap data with hierarchical structure
    # Top level: Asset Classes (Domestic, International, Property, Bonds/Cash, Crypto, etc.)
    treemap_children = []

    # Collect all holdings across investment accounts (retirement + taxable)
    # Exclude crypto accounts to avoid double counting
    all_investment_holdings = []
    for account in accounts:
        if account.account_type != AccountType.CRYPTO and account.id in holdings_by_account:
            for holding in holdings_by_account[account.id]:
                if holding.current_total_value:
                    all_investment_holdings.append(holding)

    # Separate into asset classes with market cap classification
    domestic_stocks_dict = {}
    international_stocks_dict = {}
    bonds_dict = {}
    cash_dict = {}
    other_dict = {}

    # TODO: Replace with external financial data API (Alpha Vantage, Polygon.io, etc.)
    # and store classifications in holding.market_cap and holding.asset_class columns

    # Common ticker patterns (used as fallback, not exhaustive)
    # Primary classification uses fund name parsing
    COMMON_PATTERNS = {
        "cash": {"VMFXX", "SPAXX", "FDRXX", "SWVXX", "VMMXX"},
        "bonds": {"AGG", "BND", "BNDX", "TLT", "VBTLX", "FBNDX"},
        "large_cap": {"SPY", "VOO", "IVV", "QQQ", "VV", "SCHX"},
        "mid_cap": {"MDY", "IJH", "VO", "SCHM", "IVOO"},
        "small_cap": {"IWM", "IJR", "VB", "SCHA", "VTWO"},
    }

    def classify_market_cap(ticker: str, name: str = None, asset_type: str = None) -> str:
        """
        Classify market cap using intelligent name parsing.

        Strategy:
        1. Parse fund name for explicit cap size (e.g., "Vanguard Large Cap Index")
        2. Check against common ETF patterns as fallback
        3. Use asset_type to make educated defaults

        Returns: 'Large Cap', 'Mid Cap', or 'Small Cap'
        """
        name_upper = (name or "").upper()
        ticker_upper = ticker.upper()

        # Strategy 1: Intelligent name parsing (most reliable for mutual funds/ETFs)
        if name_upper:
            # Look for explicit cap size mentions with word boundaries
            if re.search(r"\b(LARGE[\s-]?CAP|MEGA[\s-]?CAP|LARGECAP)\b", name_upper):
                return "Large Cap"
            if re.search(r"\b(MID[\s-]?CAP|MIDCAP)\b", name_upper):
                return "Mid Cap"
            if re.search(r"\b(SMALL[\s-]?CAP|MICRO[\s-]?CAP|SMALLCAP)\b", name_upper):
                return "Small Cap"

            # Check for standalone 'LARGE', 'MID', 'SMALL' keywords
            if re.search(r"\bLARGE\b", name_upper):
                return "Large Cap"
            if re.search(r"\bMID\b", name_upper):
                return "Mid Cap"
            if re.search(r"\bSMALL\b", name_upper):
                return "Small Cap"

        # Strategy 2: Common ETF ticker fallback
        if ticker_upper in COMMON_PATTERNS["large_cap"]:
            return "Large Cap"
        if ticker_upper in COMMON_PATTERNS["mid_cap"]:
            return "Mid Cap"
        if ticker_upper in COMMON_PATTERNS["small_cap"]:
            return "Small Cap"

        # Strategy 3: Default based on asset type (most holdings are large cap)
        return "Large Cap"

    domestic_stocks_value = Decimal("0")
    international_value_from_holdings = Decimal("0")
    bonds_value = Decimal("0")
    cash_from_holdings = Decimal("0")
    other_investments = Decimal("0")

    # Store holdings with metadata for cap classification
    domestic_stocks_with_cap = []  # List of (ticker, value, cap_size, name)
    international_stocks_with_cap = []  # List of (ticker, value, cap_size, name, country)

    def is_cash_holding(ticker: str, name: str, asset_type: str) -> bool:
        """Identify cash/money market holdings."""
        ticker_upper = ticker.upper()
        name_upper = (name or "").upper()

        # Check common patterns first
        if ticker_upper in COMMON_PATTERNS["cash"]:
            return True

        # Parse name for money market keywords
        if any(
            keyword in name_upper for keyword in ["MONEY MARKET", "CASH", "SWEEP", "SETTLEMENT"]
        ):
            return True

        # Check asset type if available
        if asset_type == "cash":
            return True

        return False

    def is_bond_holding(ticker: str, name: str, asset_type: str) -> bool:
        """Identify bond holdings."""
        ticker_upper = ticker.upper()
        name_upper = (name or "").upper()

        # Check common patterns first
        if ticker_upper in COMMON_PATTERNS["bonds"]:
            return True

        # Parse name for bond keywords
        if any(
            keyword in name_upper
            for keyword in ["BOND", "TREASURY", "GOVT", "FIXED INCOME", "CORPORATE DEBT"]
        ):
            return True

        # Check ticker patterns
        if any(pattern in ticker_upper for pattern in ["BND", "BOND", "TLT", "AGG"]):
            return True

        # Check asset type
        if asset_type == "bond":
            return True

        return False

    for holding in all_investment_holdings:
        ticker = holding.ticker.upper()
        value = holding.current_total_value
        name = holding.name or ""
        asset_type = holding.asset_type or ""
        asset_class = (holding.asset_class or "").lower()
        country = holding.country or ""

        if is_cash_holding(ticker, name, asset_type):
            # Cash/Money Market
            cash_from_holdings += value
            if ticker in cash_dict:
                cash_dict[ticker] += value
            else:
                cash_dict[ticker] = value
        elif is_bond_holding(ticker, name, asset_type):
            # Bonds
            bonds_value += value
            if ticker in bonds_dict:
                bonds_dict[ticker] += value
            else:
                bonds_dict[ticker] = value
        elif (
            asset_class == "international"
            or (ticker in international_tickers)
            or (country and country not in ["USA", "US", "United States", ""])
        ):
            # International - check asset_class first, then fallback to hardcoded list or country
            international_value_from_holdings += value
            cap_size = classify_market_cap(ticker, name, asset_type)
            international_stocks_with_cap.append((ticker, value, cap_size, name, country))
            if ticker in international_stocks_dict:
                international_stocks_dict[ticker] += value
            else:
                international_stocks_dict[ticker] = value
        elif asset_type in ["stock", "etf", "mutual_fund"]:
            # Domestic stocks/equities
            domestic_stocks_value += value
            cap_size = classify_market_cap(ticker, name, asset_type)
            domestic_stocks_with_cap.append((ticker, value, cap_size, name))
            if ticker in domestic_stocks_dict:
                domestic_stocks_dict[ticker] += value
            else:
                domestic_stocks_dict[ticker] = value
        else:
            # Other
            other_investments += value
            if ticker in other_dict:
                other_dict[ticker] += value
            else:
                other_dict[ticker] = value

    # Handle investment accounts with balances but no holdings (e.g., not yet synced)
    investment_accounts_without_holdings_value = Decimal("0")
    investment_accounts_without_holdings_dict = {}  # {account_name: value}

    for account in accounts:
        if account.account_type in INVESTMENT_ACCOUNT_TYPES and account.current_balance:
            # Check if this account has any holdings
            if account.id not in holdings_by_account or len(holdings_by_account[account.id]) == 0:
                # Account has a balance but no holdings - include it
                investment_accounts_without_holdings_value += account.current_balance
                investment_accounts_without_holdings_dict[account.name] = account.current_balance

    # Calculate property, vehicle, crypto, and bank account values
    property_value = Decimal("0")
    for account in accounts:
        if account.account_type == AccountType.PROPERTY and account.current_balance:
            property_value += account.current_balance

    vehicle_value = Decimal("0")
    for account in accounts:
        if account.account_type == AccountType.VEHICLE and account.current_balance:
            vehicle_value += account.current_balance

    # Collect checking and savings accounts for cash category
    checking_accounts = []
    savings_accounts = []
    checking_value = Decimal("0")
    savings_value = Decimal("0")

    for account in accounts:
        if account.account_type == AccountType.CHECKING and account.current_balance:
            checking_value += account.current_balance
            checking_accounts.append(account)
        elif account.account_type == AccountType.SAVINGS and account.current_balance:
            savings_value += account.current_balance
            savings_accounts.append(account)

    crypto_value = Decimal("0")
    crypto_holdings_dict_prelim = {}
    for account in accounts:
        if account.account_type == AccountType.CRYPTO:
            # If account has holdings records, use those
            if account.id in holdings_by_account:
                for holding in holdings_by_account[account.id]:
                    if holding.current_total_value:
                        crypto_value += holding.current_total_value
                        ticker = holding.ticker
                        if ticker in crypto_holdings_dict_prelim:
                            crypto_holdings_dict_prelim[ticker] += holding.current_total_value
                        else:
                            crypto_holdings_dict_prelim[ticker] = holding.current_total_value
            # If account has no holdings but has a balance, use account balance as fallback
            elif account.current_balance and account.current_balance > 0:
                crypto_value += account.current_balance
                # Add placeholder for treemap (use account name as "ticker")
                ticker_name = f"{account.name} (Balance)"
                crypto_holdings_dict_prelim[ticker_name] = account.current_balance

    # Create treemap nodes for each asset class
    total_cash = cash_from_holdings + checking_value + savings_value
    portfolio_total = (
        domestic_stocks_value
        + international_value_from_holdings
        + bonds_value
        + total_cash
        + other_investments
        + property_value
        + vehicle_value
        + crypto_value
        + investment_accounts_without_holdings_value
    )

    # Add Domestic Stocks with market cap layers
    if domestic_stocks_value > 0:
        # Group by market cap
        cap_groups = {}  # {cap_size: [(ticker, value), ...]}
        for ticker, value, cap_size, name in domestic_stocks_with_cap:
            if cap_size not in cap_groups:
                cap_groups[cap_size] = []
            cap_groups[cap_size].append((ticker, value))

        # Create cap size nodes
        cap_children = []
        cap_colors = {
            "Large Cap": "#2B6CB0",  # darker blue
            "Mid Cap": "#4299E1",  # medium blue
            "Small Cap": "#63B3ED",  # lighter blue
        }
        for cap_size in ["Large Cap", "Mid Cap", "Small Cap"]:
            if cap_size in cap_groups:
                cap_value = sum(value for _, value in cap_groups[cap_size])
                ticker_nodes = [
                    TreemapNode(name=ticker, value=value, percent=(value / cap_value * 100))
                    for ticker, value in cap_groups[cap_size]
                ]
                cap_children.append(
                    TreemapNode(
                        name=cap_size,
                        value=cap_value,
                        percent=(cap_value / domestic_stocks_value * 100),
                        children=ticker_nodes,
                        color=cap_colors.get(cap_size, "#4299E1"),
                    )
                )

        treemap_children.append(
            TreemapNode(
                name="Domestic Stocks",
                value=domestic_stocks_value,
                percent=(
                    (domestic_stocks_value / portfolio_total * 100)
                    if portfolio_total > 0
                    else Decimal("0")
                ),
                children=cap_children,
                color="#4299E1",  # blue
            )
        )

    # Add International with Developed/Emerging market layers
    if international_value_from_holdings > 0:
        # Define emerging markets (developed markets are the default)
        EMERGING_MARKETS = {
            "China",
            "CN",
            "CHN",
            "Taiwan",
            "TW",
            "TWN",
            "India",
            "IN",
            "IND",
            "Brazil",
            "BR",
            "BRA",
            "Russia",
            "RU",
            "RUS",
            "South Africa",
            "ZA",
            "ZAF",
            "Mexico",
            "MX",
            "MEX",
            "Indonesia",
            "ID",
            "IDN",
            "Turkey",
            "TR",
            "TUR",
            "Saudi Arabia",
            "SA",
            "SAU",
            "Poland",
            "PL",
            "POL",
            "Thailand",
            "TH",
            "THA",
            "Malaysia",
            "MY",
            "MYS",
            "Philippines",
            "PH",
            "PHL",
            "Colombia",
            "CO",
            "COL",
            "Chile",
            "CL",
            "CHL",
            "Peru",
            "PE",
            "PER",
            "Egypt",
            "EG",
            "EGY",
            "UAE",
            "AE",
            "ARE",
            "Qatar",
            "QA",
            "QAT",
            "Argentina",
            "AR",
            "ARG",
            "Pakistan",
            "PK",
            "PAK",
            "Vietnam",
            "VN",
            "VNM",
            "Bangladesh",
            "BD",
            "BGD",
        }

        # Group by developed vs emerging markets
        developed_holdings = []  # List of (ticker, value)
        emerging_holdings = []  # List of (ticker, value)

        for ticker, value, cap_size, name, country in international_stocks_with_cap:
            if country in EMERGING_MARKETS:
                emerging_holdings.append((ticker, value))
            else:
                # Default to developed (includes Global funds and unrecognized countries)
                developed_holdings.append((ticker, value))

        # Create region nodes
        intl_region_children = []

        if developed_holdings:
            developed_value = sum(value for _, value in developed_holdings)
            developed_ticker_nodes = [
                TreemapNode(name=ticker, value=value, percent=(value / developed_value * 100))
                for ticker, value in developed_holdings
            ]
            intl_region_children.append(
                TreemapNode(
                    name="International - Developed",
                    value=developed_value,
                    percent=(developed_value / international_value_from_holdings * 100),
                    children=developed_ticker_nodes,
                    color="#6B46C1",  # darker purple
                )
            )

        if emerging_holdings:
            emerging_value = sum(value for _, value in emerging_holdings)
            emerging_ticker_nodes = [
                TreemapNode(name=ticker, value=value, percent=(value / emerging_value * 100))
                for ticker, value in emerging_holdings
            ]
            intl_region_children.append(
                TreemapNode(
                    name="International - Emerging",
                    value=emerging_value,
                    percent=(emerging_value / international_value_from_holdings * 100),
                    children=emerging_ticker_nodes,
                    color="#9F7AEA",  # lighter purple
                )
            )

        treemap_children.append(
            TreemapNode(
                name="International",
                value=international_value_from_holdings,
                percent=(
                    (international_value_from_holdings / portfolio_total * 100)
                    if portfolio_total > 0
                    else Decimal("0")
                ),
                children=intl_region_children,
                color="#805AD5",  # purple
            )
        )

    # Add Bonds
    if bonds_value > 0:
        bond_holdings = [
            TreemapNode(name=ticker, value=value, percent=(value / bonds_value * 100))
            for ticker, value in bonds_dict.items()
        ]
        treemap_children.append(
            TreemapNode(
                name="Bonds",
                value=bonds_value,
                percent=(
                    (bonds_value / portfolio_total * 100) if portfolio_total > 0 else Decimal("0")
                ),
                children=bond_holdings,
                color="#48BB78",  # green
            )
        )

    # Add Cash with subcategories (Money Market, Savings, Checking)
    if total_cash > 0:
        cash_subcategories = []

        # Money Market (from holdings)
        if cash_from_holdings > 0:
            money_market_holdings = [
                TreemapNode(name=ticker, value=value, percent=(value / cash_from_holdings * 100))
                for ticker, value in cash_dict.items()
            ]
            cash_subcategories.append(
                TreemapNode(
                    name="Money Market",
                    value=cash_from_holdings,
                    percent=(cash_from_holdings / total_cash * 100),
                    children=money_market_holdings,
                    color="#2C7A7B",  # darker teal
                )
            )

        # Savings Accounts
        if savings_value > 0:
            savings_nodes = [
                TreemapNode(
                    name=account.name,
                    value=account.current_balance,
                    percent=(account.current_balance / savings_value * 100),
                )
                for account in savings_accounts
            ]
            cash_subcategories.append(
                TreemapNode(
                    name="Savings",
                    value=savings_value,
                    percent=(savings_value / total_cash * 100),
                    children=savings_nodes,
                    color="#38B2AC",  # medium teal
                )
            )

        # Checking Accounts
        if checking_value > 0:
            checking_nodes = [
                TreemapNode(
                    name=account.name,
                    value=account.current_balance,
                    percent=(account.current_balance / checking_value * 100),
                )
                for account in checking_accounts
            ]
            cash_subcategories.append(
                TreemapNode(
                    name="Checking",
                    value=checking_value,
                    percent=(checking_value / total_cash * 100),
                    children=checking_nodes,
                    color="#4FD1C5",  # lighter teal
                )
            )

        treemap_children.append(
            TreemapNode(
                name="Cash",
                value=total_cash,
                percent=(
                    (total_cash / portfolio_total * 100) if portfolio_total > 0 else Decimal("0")
                ),
                children=cash_subcategories,
                color="#38B2AC",  # teal
            )
        )

    # Add Property & Vehicles (with subcategories)
    property_and_vehicles_value = property_value + vehicle_value
    if property_and_vehicles_value > 0:
        property_and_vehicle_subcategories = []

        # Real Estate subcategory
        if property_value > 0:
            property_accounts = []
            for account in accounts:
                if account.account_type == AccountType.PROPERTY and account.current_balance:
                    property_accounts.append(
                        TreemapNode(
                            name=account.name,
                            value=account.current_balance,
                            percent=(account.current_balance / property_value * 100),
                        )
                    )
            property_and_vehicle_subcategories.append(
                TreemapNode(
                    name="Real Estate",
                    value=property_value,
                    percent=(property_value / property_and_vehicles_value * 100),
                    children=property_accounts,
                    color="#DD6B20",  # darker orange
                )
            )

        # Vehicles subcategory
        if vehicle_value > 0:
            vehicle_accounts = []
            for account in accounts:
                if account.account_type == AccountType.VEHICLE and account.current_balance:
                    vehicle_accounts.append(
                        TreemapNode(
                            name=account.name,
                            value=account.current_balance,
                            percent=(account.current_balance / vehicle_value * 100),
                        )
                    )
            property_and_vehicle_subcategories.append(
                TreemapNode(
                    name="Vehicles",
                    value=vehicle_value,
                    percent=(vehicle_value / property_and_vehicles_value * 100),
                    children=vehicle_accounts,
                    color="#ED8936",  # lighter orange
                )
            )

        treemap_children.append(
            TreemapNode(
                name="Property & Vehicles",
                value=property_and_vehicles_value,
                percent=(
                    (property_and_vehicles_value / portfolio_total * 100)
                    if portfolio_total > 0
                    else Decimal("0")
                ),
                children=(
                    property_and_vehicle_subcategories
                    if property_and_vehicle_subcategories
                    else None
                ),
                color="#ED8936",  # orange
            )
        )

    # Add Crypto
    if crypto_value > 0:
        crypto_holdings = [
            TreemapNode(name=ticker, value=value, percent=(value / crypto_value * 100))
            for ticker, value in crypto_holdings_dict_prelim.items()
        ]
        treemap_children.append(
            TreemapNode(
                name="Crypto",
                value=crypto_value,
                percent=(
                    (crypto_value / portfolio_total * 100) if portfolio_total > 0 else Decimal("0")
                ),
                children=crypto_holdings,
                color="#9F7AEA",  # purple (different shade than international)
            )
        )

    # Add Other
    if other_investments > 0:
        other_holdings = [
            TreemapNode(name=ticker, value=value, percent=(value / other_investments * 100))
            for ticker, value in other_dict.items()
        ]
        treemap_children.append(
            TreemapNode(
                name="Other",
                value=other_investments,
                percent=(
                    (other_investments / portfolio_total * 100)
                    if portfolio_total > 0
                    else Decimal("0")
                ),
                children=other_holdings,
                color="#A0AEC0",  # gray
            )
        )

    # Add Investment Accounts Without Holdings (accounts with balance but no holdings data)
    if investment_accounts_without_holdings_value > 0:
        account_nodes = [
            TreemapNode(
                name=f"{account_name} (Holdings Unknown)",
                value=value,
                percent=(value / investment_accounts_without_holdings_value * 100),
            )
            for account_name, value in investment_accounts_without_holdings_dict.items()
        ]
        treemap_children.append(
            TreemapNode(
                name="Investment Accounts",
                value=investment_accounts_without_holdings_value,
                percent=(
                    (investment_accounts_without_holdings_value / portfolio_total * 100)
                    if portfolio_total > 0
                    else Decimal("0")
                ),
                children=account_nodes,
                color="#4299E1",  # blue for investment accounts
            )
        )

    # Create root treemap node
    logger.info(f"Creating treemap with {len(treemap_children)} top-level children")
    treemap_data = (
        TreemapNode(
            name="Portfolio",
            value=portfolio_total,
            percent=Decimal("100"),
            children=treemap_children,
        )
        if treemap_children
        else None
    )

    # Update total_value to portfolio_total for summary stats
    total_value = portfolio_total

    # Group holdings by account for detailed view
    # Include investment and investment-like accounts (exclude checking, credit cards, loans)
    holdings_by_account_list = []
    for account in accounts:
        # Skip non-investment accounts
        if account.account_type not in INVESTMENT_ACCOUNT_TYPES:
            continue

        # Get holdings for this account (empty list if none)
        account_holdings = holdings_by_account.get(account.id, [])

        # Use account's current_balance as the authoritative value
        # Fall back to summing holdings if current_balance is not set
        if account.current_balance:
            account_total = account.current_balance
        else:
            account_total = sum((h.current_total_value or Decimal("0")) for h in account_holdings)

        holdings_by_account_list.append(
            AccountHoldings(
                account_id=account.id,
                account_name=account.name,
                account_type=account.account_type.value,
                account_value=account_total,
                holdings=[HoldingSchema.model_validate(h) for h in account_holdings],
            )
        )

    # Sort by account value (largest first)
    holdings_by_account_list.sort(key=lambda x: x.account_value, reverse=True)

    logger.info(f"Returning portfolio summary with total value: {total_value}")
    summary = PortfolioSummary(
        total_value=total_value,
        total_cost_basis=total_cost_basis if total_cost_basis else None,
        total_gain_loss=total_gain_loss,
        total_gain_loss_percent=total_gain_loss_percent,
        holdings_by_ticker=holdings_summaries,
        holdings_by_account=holdings_by_account_list,
        stocks_value=stocks_value,
        bonds_value=bonds_value,
        etf_value=etf_value,
        mutual_funds_value=mutual_funds_value,
        cash_value=cash_value,
        other_value=other_value,
        category_breakdown=category_breakdown,
        geographic_breakdown=geographic_breakdown,
        treemap_data=treemap_data,
        sector_breakdown=sector_breakdown,
        total_annual_fees=total_annual_fees if total_annual_fees > 0 else None,
    )

    # Cache the serialized response (fail-open on Redis errors)
    await cache_setex(cache_key, 300, summary.model_dump(mode="json"))

    return summary


@router.get("/account/{account_id}", response_model=List[HoldingSchema])
async def get_account_holdings(
    response: Response,
    account: Account = Depends(get_verified_account),
    db: AsyncSession = Depends(get_db),
    after_ticker: Optional[str] = Query(
        None, description="Cursor: return holdings with ticker > this value"
    ),
    limit: int = Query(100, ge=1, le=500, description="Max holdings to return"),
):
    """Get holdings for a specific account with keyset pagination."""
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(Holding).where(Holding.account_id == account.id)
    )
    total_count = count_result.scalar()

    # Build keyset-paginated query
    query = select(Holding).where(Holding.account_id == account.id)
    if after_ticker:
        query = query.where(Holding.ticker > after_ticker)
    query = query.order_by(Holding.ticker).limit(limit)

    result = await db.execute(query)
    holdings = result.scalars().all()

    # Set total count header for client pagination
    response.headers["X-Total-Count"] = str(total_count)

    return holdings


@router.post("/", response_model=HoldingSchema, status_code=201)
async def create_holding(
    holding_data: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new holding."""
    logger = logging.getLogger(__name__)

    # Verify account belongs to user's organization
    account_result = await db.execute(
        select(Account).where(
            Account.id == holding_data.account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        logger.warning(
            "create_holding: account not found account_id=%s user_id=%s",
            holding_data.account_id,
            current_user.id,
        )
        raise HTTPException(status_code=404, detail="Account not found")

    # Verify account is an investment or crypto type
    if account.account_type not in INVESTMENT_ACCOUNT_TYPES:
        logger.warning(
            "create_holding: invalid account type account_id=%s type=%s user_id=%s",
            account.id,
            account.account_type,
            current_user.id,
        )
        raise HTTPException(
            status_code=400, detail="Holdings can only be added to investment and crypto accounts"
        )

    # Calculate cost basis
    total_cost_basis = None
    if holding_data.cost_basis_per_share:
        total_cost_basis = holding_data.shares * holding_data.cost_basis_per_share

    # Sanitize user text input
    sanitized_name = (
        input_sanitization_service.sanitize_html(holding_data.name)
        if holding_data.name
        else holding_data.name
    )

    # Create holding
    holding = Holding(
        account_id=holding_data.account_id,
        organization_id=current_user.organization_id,
        ticker=holding_data.ticker.upper(),  # Normalize to uppercase
        name=sanitized_name,
        shares=holding_data.shares,
        cost_basis_per_share=holding_data.cost_basis_per_share,
        total_cost_basis=total_cost_basis,
        asset_type=holding_data.asset_type,
    )

    db.add(holding)
    await db.commit()
    await db.refresh(holding)

    # Invalidate portfolio summary cache
    await cache_delete_pattern(f"portfolio:summary:{current_user.organization_id}:*")

    logger.info(
        "create_holding: ticker=%s shares=%s account_id=%s user_id=%s org_id=%s",
        holding.ticker,
        holding.shares,
        account.id,
        current_user.id,
        current_user.organization_id,
    )

    # Immediately fetch current price in background (non-blocking)
    _task = _asyncio.create_task(_fetch_price_for_holding(holding.id, holding.ticker))
    _background_tasks.add(_task)
    _task.add_done_callback(_background_tasks.discard)

    return holding


# Strong references to background tasks to prevent GC from cancelling them
_background_tasks: set[_asyncio.Task] = set()


async def _fetch_price_for_holding(holding_id, ticker: str) -> None:
    """
    Background task: fetch and store the current price for a newly created holding.
    Silently swallows errors so it never affects the create response.
    """
    try:
        market_data = get_market_data_provider()
        quote = await market_data.get_quote(ticker)

        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_update(Holding)
                .where(Holding.id == holding_id)
                .values(
                    current_price_per_share=quote.price,
                    price_as_of=datetime.now(timezone.utc),
                )
            )
            await db.commit()

        logging.getLogger(__name__).info(
            "holding_price_fetch: ticker=%s price=%s", ticker, quote.price
        )
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "holding_price_fetch failed for ticker=%s (non-critical): %s", ticker, exc
        )


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
        holding.name = input_sanitization_service.sanitize_html(holding_data.name)
    if holding_data.shares is not None:
        holding.shares = holding_data.shares
    if holding_data.cost_basis_per_share is not None:
        holding.cost_basis_per_share = holding_data.cost_basis_per_share
        # Recalculate total cost basis
        holding.total_cost_basis = holding.shares * holding_data.cost_basis_per_share
    if holding_data.current_price_per_share is not None:
        holding.current_price_per_share = holding_data.current_price_per_share
        holding.current_total_value = holding.shares * holding_data.current_price_per_share
        holding.price_as_of = utc_now()
    if holding_data.asset_type is not None:
        holding.asset_type = holding_data.asset_type

    holding.updated_at = utc_now()

    await db.commit()
    await db.refresh(holding)

    # Invalidate portfolio summary cache
    await cache_delete_pattern(f"portfolio:summary:{current_user.organization_id}:*")

    return holding


@router.delete("/{holding_id}", status_code=204)
async def delete_holding(
    holding_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a holding."""
    logger = logging.getLogger(__name__)

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

    logger.info(
        "delete_holding: ticker=%s account_id=%s user_id=%s",
        holding.ticker,
        holding.account_id,
        current_user.id,
    )

    await db.delete(holding)
    await db.commit()

    # Invalidate portfolio summary cache
    await cache_delete_pattern(f"portfolio:summary:{current_user.organization_id}:*")

    return None


@router.post("/capture-snapshot", response_model=SnapshotResponse)
async def capture_portfolio_snapshot(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Capture a portfolio snapshot for today.

    Creates or updates a snapshot of the current portfolio state.
    Used for historical performance tracking.
    """
    # Get current portfolio summary
    portfolio = await get_portfolio_summary(current_user=current_user, db=db)

    # Capture snapshot
    snapshot = await snapshot_service.capture_snapshot(
        db=db,
        organization_id=current_user.organization_id,
        portfolio=portfolio,
    )

    return snapshot


@router.get("/historical", response_model=List[SnapshotResponse])
async def get_historical_snapshots(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(None, ge=1, le=5000, description="Maximum number of snapshots"),
    user_id: Optional[UUID] = Query(
        None,
        description="Filter by user ID. Omit for household-level snapshots.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical portfolio snapshots.

    Returns snapshots ordered by date ascending for charting.

    Query parameters:
    - start_date: Start date (defaults to 1 year ago)
    - end_date: End date (defaults to today)
    - limit: Maximum number of snapshots to return (max 5000)
    - user_id: Filter by user. Omit for whole-household snapshots.
    """
    # Default to last year if no start date provided
    if start_date is None:
        start_date = date.today() - timedelta(days=365)

    if start_date and end_date:
        validate_date_range(start_date, end_date)

    # If user_id provided, verify they belong to the same household
    if user_id is not None:
        await verify_household_member(
            user_id=user_id,
            organization_id=current_user.organization_id,
            db=db,
        )

    snapshots = await snapshot_service.get_snapshots(
        db=db,
        organization_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        user_id=user_id,
    )

    return snapshots


@router.get("/style-box", response_model=List[StyleBoxItem])
async def get_style_box_breakdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive asset allocation breakdown including:
    - Market cap and style (Large/Mid/Small Cap × Value/Core/Growth)
    - International stocks (Developed/Emerging markets)
    - Cash holdings (Money Market, Checking, Savings)
    - Real estate exposure (from fund composition)
    """

    # Get all holdings for the organization
    result = await db.execute(
        select(Holding)
        .where(Holding.organization_id == current_user.organization_id)
        .options(selectinload(Holding.account))
    )
    holdings = result.scalars().all()

    # Filter to investment accounts only
    investment_holdings = [
        h for h in holdings if h.account and h.account.account_type in INVESTMENT_ACCOUNT_TYPES
    ]

    # Also get cash accounts for Cash breakdown
    cash_accounts_result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.account_type.in_(CASH_ACCOUNT_TYPES),
            Account.is_active.is_(True),
        )
    )
    cash_accounts = cash_accounts_result.scalars().all()

    if not investment_holdings and not cash_accounts:
        return []

    # Calculate total portfolio value (investments + cash)
    investment_value = sum(
        (h.shares or Decimal("0")) * (h.current_price_per_share or Decimal("0"))
        for h in investment_holdings
    )
    cash_value = sum(acc.current_balance or Decimal("0") for acc in cash_accounts)
    total_value = investment_value + cash_value

    if total_value == 0:
        return []

    # Developed and Emerging market country lists
    DEVELOPED_MARKETS = {
        "USA",
        "US",
        "United States",
        "UK",
        "United Kingdom",
        "GB",
        "GBR",
        "Germany",
        "DE",
        "DEU",
        "Japan",
        "JP",
        "JPN",
        "Canada",
        "CA",
        "CAN",
        "France",
        "FR",
        "FRA",
        "Switzerland",
        "CH",
        "CHE",
        "Australia",
        "AU",
        "AUS",
        "Netherlands",
        "NL",
        "NLD",
        "Sweden",
        "SE",
        "SWE",
        "Denmark",
        "DK",
        "DNK",
        "Norway",
        "NO",
        "NOR",
        "Finland",
        "FI",
        "FIN",
        "Spain",
        "ES",
        "ESP",
        "Italy",
        "IT",
        "ITA",
        "Belgium",
        "BE",
        "BEL",
        "Austria",
        "AT",
        "AUT",
        "Singapore",
        "SG",
        "SGP",
        "Hong Kong",
        "HK",
        "HKG",
        "New Zealand",
        "NZ",
        "NZL",
    }

    EMERGING_MARKETS = {
        "China",
        "CN",
        "CHN",
        "Taiwan",
        "TW",
        "TWN",
        "India",
        "IN",
        "IND",
        "Brazil",
        "BR",
        "BRA",
        "Russia",
        "RU",
        "RUS",
        "South Africa",
        "ZA",
        "ZAF",
        "Mexico",
        "MX",
        "MEX",
        "Indonesia",
        "ID",
        "IDN",
        "Turkey",
        "TR",
        "TUR",
        "Saudi Arabia",
        "SA",
        "SAU",
        "Poland",
        "PL",
        "POL",
        "Thailand",
        "TH",
        "THA",
        "Malaysia",
        "MY",
        "MYS",
        "Philippines",
        "PH",
        "PHL",
        "Colombia",
        "CO",
        "COL",
        "Chile",
        "CL",
        "CHL",
        "Peru",
        "PE",
        "PER",
        "Egypt",
        "EG",
        "EGY",
        "UAE",
        "AE",
        "ARE",
        "Qatar",
        "QA",
        "QAT",
        "Argentina",
        "AR",
        "ARG",
        "Pakistan",
        "PK",
        "PAK",
        "Vietnam",
        "VN",
        "VNM",
        "Bangladesh",
        "BD",
        "BGD",
    }

    # Group holdings by various categories
    style_groups: dict[str, dict] = {}

    for holding in investment_holdings:
        value = (holding.shares or Decimal("0")) * (holding.current_price_per_share or Decimal("0"))
        if value == 0:
            continue

        # Check if international based on country field and asset_class
        country = holding.country or ""

        # Determine if this is an international holding
        is_international = holding.asset_class == "international" or (
            country and country not in ["USA", "US", "United States", ""]
        )

        # Skip bonds and cash equivalents from holdings (cash accounts handled separately)
        if holding.asset_class in ["bond", "cash"]:
            continue

        if is_international:
            # Categorize as Developed or Emerging market based on country
            if country in DEVELOPED_MARKETS:
                style_class = "International - Developed"
            elif country in EMERGING_MARKETS:
                style_class = "International - Emerging"
            else:
                # If country not recognized, default to Developed
                # (most international stocks are developed markets)
                style_class = "International - Developed"
        else:
            # Domestic stocks - categorize by market cap and style
            market_cap_str = (holding.market_cap or "").lower()

            # Map market cap string to display name
            if market_cap_str == "large":
                size = "Large Cap"
            elif market_cap_str == "mid":
                size = "Mid Cap"
            elif market_cap_str == "small":
                size = "Small Cap"
            else:
                # Default to Large Cap if not specified
                size = "Large Cap"

            # Infer style from asset class or default to Core
            asset_class_lower = (holding.asset_class or "").lower()
            if "value" in asset_class_lower:
                style = "Value"
            elif "growth" in asset_class_lower:
                style = "Growth"
            else:
                style = "Core"

            style_class = f"{size} {style}"

        if style_class not in style_groups:
            style_groups[style_class] = {"value": Decimal("0"), "count": 0}

        style_groups[style_class]["value"] += value
        style_groups[style_class]["count"] += 1

    # Add Cash breakdown
    if cash_value > 0:
        cash_breakdown = {}
        for account in cash_accounts:
            balance = account.current_balance or Decimal("0")
            if balance == 0:
                continue

            # Map account type to display name
            type_map = {
                AccountType.MONEY_MARKET: "Cash - Money Market",
                AccountType.CHECKING: "Cash - Checking",
                AccountType.SAVINGS: "Cash - Savings",
            }
            cash_type = type_map.get(account.account_type, "Cash - Other")

            if cash_type not in cash_breakdown:
                cash_breakdown[cash_type] = {"value": Decimal("0"), "count": 0}

            cash_breakdown[cash_type]["value"] += balance
            cash_breakdown[cash_type]["count"] += 1

        # Add cash categories to style_groups
        style_groups.update(cash_breakdown)

    # Add Real Estate category (mock data for now)
    # TODO: Implement fund composition analysis to detect real estate exposure
    # For common funds like FXIAX (Fidelity 500 Index), real estate is ~3% of S&P 500
    # For now, estimate 2-3% of large cap holdings might have real estate exposure
    real_estate_funds = ["VNQ", "VGSLX", "FREL", "IYR"]  # Known REIT tickers
    real_estate_value = Decimal("0")
    real_estate_count = 0

    for holding in investment_holdings:
        if holding.ticker.upper() in real_estate_funds:
            value = (holding.shares or Decimal("0")) * (
                holding.current_price_per_share or Decimal("0")
            )
            real_estate_value += value
            real_estate_count += 1

    # Also add estimated real estate exposure from broad index funds
    # S&P 500 funds typically have ~3% real estate sector allocation
    sp500_funds = ["FXAIX", "VOO", "IVV", "SPY"]
    for holding in investment_holdings:
        if holding.ticker.upper() in sp500_funds:
            value = (holding.shares or Decimal("0")) * (
                holding.current_price_per_share or Decimal("0")
            )
            real_estate_value += value * Decimal("0.03")  # 3% allocation

    if real_estate_value > 0:
        style_groups["Real Estate"] = {
            "value": real_estate_value,
            "count": real_estate_count if real_estate_count > 0 else 1,
        }

    # Build response with mock 1-day changes
    breakdown = []
    for style_class, data in sorted(style_groups.items()):
        percentage = (data["value"] / total_value * 100) if total_value > 0 else Decimal("0")

        # Mock 1-day change (random between -0.5% and +1.5%)
        # Cash has 0% change
        if "Cash" in style_class:
            one_day_change = Decimal("0")
        else:
            # CSPRNG: generate int in [0, 200] then shift to [-0.5, 1.5]
            one_day_change = Decimal(str(round((secrets.randbelow(201) - 50) / 100, 2)))

        breakdown.append(
            StyleBoxItem(
                style_class=style_class,
                percentage=percentage,
                one_day_change=one_day_change,
                value=data["value"],
                holding_count=data["count"],
            )
        )

    return breakdown


@router.get("/rmd-summary", response_model=None)
async def get_rmd_summary(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get Required Minimum Distribution summary for retirement accounts.

    For individual user view: Returns RMD for specified user's accounts.
    For combined household view: Returns combined RMD for all household members with birthdates.
    Only applicable if user has birthdate set and is age 73+.
    """
    # RMD-applicable retirement accounts (Traditional IRA, 401k, 403b, 457b, SEP, SIMPLE, Pension)
    # Roth accounts do NOT require RMDs during owner's lifetime
    rmd_account_types = RMD_ACCOUNT_TYPES

    # Individual user view
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

        # Get the target user
        result = await db.execute(
            select(User).where(
                User.id == user_id, User.organization_id == current_user.organization_id
            )
        )
        target_user = result.scalar_one()

        # Check if user has birthdate - if not, return null (RMD should not be displayed)
        if not target_user.birthdate:
            return None

        # Calculate user's current age
        user_age = calculate_age(target_user.birthdate)

        # Check if RMD is required
        if not requires_rmd(user_age):
            return RMDSummary(
                user_age=user_age,
                requires_rmd=False,
                rmd_deadline=None,
                total_required_distribution=Decimal("0"),
                total_distribution_taken=Decimal("0"),
                total_remaining_required=Decimal("0"),
                accounts=[],
                penalty_if_missed=None,
            )

        # Get user's accounts
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)

        # Filter for RMD-applicable accounts (exclude Roth — no RMDs during owner's lifetime)
        accounts = [
            acc
            for acc in accounts
            if acc.account_type in rmd_account_types
            and acc.is_active
            and acc.tax_treatment != TaxTreatment.ROTH
        ]

        total_required = Decimal("0")
        total_taken = Decimal("0")
        account_rmds = []

        for account in accounts:
            if not account.current_balance or account.current_balance <= 0:
                continue

            # Calculate RMD for this account
            rmd_amount = calculate_rmd(account.current_balance, user_age)

            if rmd_amount:
                total_required += rmd_amount
                distribution_taken = Decimal("0")
                remaining = rmd_amount - distribution_taken

                account_rmds.append(
                    AccountRMD(
                        account_id=account.id,
                        account_name=account.name,
                        account_type=account.account_type.value,
                        account_balance=account.current_balance,
                        required_distribution=rmd_amount,
                        distribution_taken=distribution_taken,
                        remaining_required=remaining,
                    )
                )

        total_remaining = total_required - total_taken
        penalty = calculate_rmd_penalty(total_remaining) if total_remaining > 0 else None

        return RMDSummary(
            user_age=user_age,
            requires_rmd=True,
            rmd_deadline=get_rmd_deadline(date.today().year),
            total_required_distribution=total_required,
            total_distribution_taken=total_taken,
            total_remaining_required=total_remaining,
            accounts=account_rmds,
            penalty_if_missed=penalty,
        )

    # Combined household view
    else:
        # Get all household members with birthdates
        result = await db.execute(
            select(User).where(
                User.organization_id == current_user.organization_id,
                User.is_active.is_(True),
                User.birthdate.isnot(None),
            )
        )
        household_members = result.scalars().all()

        # If no household members have birthdates, return null (RMD should not be displayed)
        if not household_members:
            return None

        # Calculate combined RMD across all members
        total_required = Decimal("0")
        total_taken = Decimal("0")
        account_rmds = []
        oldest_age = 0  # Track oldest member for response

        for member in household_members:
            member_age = calculate_age(member.birthdate)
            oldest_age = max(oldest_age, member_age)

            # Skip members who don't require RMD yet
            if not requires_rmd(member_age):
                continue

            # Get member's accounts
            member_accounts = await get_user_accounts(db, member.id, current_user.organization_id)

            # Filter for RMD-applicable accounts (exclude Roth — no RMDs during owner's lifetime)
            member_accounts = [
                acc
                for acc in member_accounts
                if acc.account_type in rmd_account_types
                and acc.is_active
                and acc.tax_treatment != TaxTreatment.ROTH
            ]

            for account in member_accounts:
                if not account.current_balance or account.current_balance <= 0:
                    continue

                # Calculate RMD for this account based on the member's age
                rmd_amount = calculate_rmd(account.current_balance, member_age)

                if rmd_amount:
                    total_required += rmd_amount
                    distribution_taken = Decimal("0")
                    remaining = rmd_amount - distribution_taken

                    account_rmds.append(
                        AccountRMD(
                            account_id=account.id,
                            account_name=account.name,
                            account_type=account.account_type.value,
                            account_balance=account.current_balance,
                            required_distribution=rmd_amount,
                            distribution_taken=distribution_taken,
                            remaining_required=remaining,
                        )
                    )

        # Check if anyone requires RMD
        if total_required == 0:
            return RMDSummary(
                user_age=oldest_age,
                requires_rmd=False,
                rmd_deadline=None,
                total_required_distribution=Decimal("0"),
                total_distribution_taken=Decimal("0"),
                total_remaining_required=Decimal("0"),
                accounts=[],
                penalty_if_missed=None,
            )

        total_remaining = total_required - total_taken
        penalty = calculate_rmd_penalty(total_remaining) if total_remaining > 0 else None

        return RMDSummary(
            user_age=oldest_age,  # Show oldest member's age for combined view
            requires_rmd=True,
            rmd_deadline=get_rmd_deadline(date.today().year),
            total_required_distribution=total_required,
            total_distribution_taken=total_taken,
            total_remaining_required=total_remaining,
            accounts=account_rmds,
            penalty_if_missed=penalty,
        )


@router.get("/roth-analysis")
async def get_roth_analysis(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = requester's own accounts"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return traditional IRA/401k balance data for Roth conversion analysis.

    Uses the tax_treatment field to distinguish Traditional (pre_tax) from Roth
    accounts. A Roth 401(k) will NOT appear here — only pre-tax retirement
    accounts are eligible for Roth conversion.
    """
    retirement_types = ROTH_CONVERSION_ELIGIBLE_TYPES

    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        user_result = await db.execute(select(User).where(User.id == user_id))
        target_user = user_result.scalar_one_or_none()
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)
        target_user = current_user

    # Only include pre-tax retirement accounts (eligible for Roth conversion).
    # Accounts with tax_treatment=ROTH are already Roth and excluded.
    # Accounts with NULL tax_treatment on retirement types default to traditional.
    traditional_accounts = [
        acc
        for acc in accounts
        if acc.account_type in retirement_types
        and acc.is_active
        and acc.tax_treatment != TaxTreatment.ROTH
    ]

    traditional_balance = sum((acc.current_balance or Decimal("0")) for acc in traditional_accounts)

    # Projected RMD at age 73 using current balance as a baseline estimate
    projected_rmd_at_73 = (
        calculate_rmd(traditional_balance, 73) if traditional_balance > 0 else None
    )

    current_age: Optional[int] = None
    if target_user and target_user.birthdate:
        current_age = calculate_age(target_user.birthdate)

    return {
        "traditional_balance": float(traditional_balance),
        "projected_rmd_at_73": float(projected_rmd_at_73) if projected_rmd_at_73 else None,
        "current_age": current_age,
        "accounts": [
            {
                "id": str(acc.id),
                "name": acc.name,
                "balance": float(acc.current_balance or 0),
                "type": acc.account_type.value,
                "tax_treatment": acc.tax_treatment.value if acc.tax_treatment else None,
            }
            for acc in traditional_accounts
        ],
    }


# ── Fund mapping data for overlap detection and low-cost alternatives ────────

# Maps common ETFs/mutual funds to their underlying index/category
FUND_INDEX_MAP: dict[str, str] = {
    # Total US Stock Market
    "VTI": "Total US Stock Market",
    "VTSAX": "Total US Stock Market",
    "ITOT": "Total US Stock Market",
    "SPTM": "Total US Stock Market",
    "SCHB": "Total US Stock Market",
    "FSKAX": "Total US Stock Market",
    "FZROX": "Total US Stock Market",
    # S&P 500
    "SPY": "S&P 500",
    "VOO": "S&P 500",
    "IVV": "S&P 500",
    "VFIAX": "S&P 500",
    "FXAIX": "S&P 500",
    "SWPPX": "S&P 500",
    "SPLG": "S&P 500",
    # Total International Stock
    "VXUS": "Total International Stock",
    "VTIAX": "Total International Stock",
    "IXUS": "Total International Stock",
    "FTIHX": "Total International Stock",
    "FZILX": "Total International Stock",
    # International Developed
    "VEA": "International Developed Markets",
    "EFA": "International Developed Markets",
    "IEFA": "International Developed Markets",
    "SWISX": "International Developed Markets",
    "SCHF": "International Developed Markets",
    # Emerging Markets
    "VWO": "Emerging Markets",
    "EEM": "Emerging Markets",
    "IEMG": "Emerging Markets",
    "SCHE": "Emerging Markets",
    # Total US Bond Market
    "BND": "Total US Bond Market",
    "AGG": "Total US Bond Market",
    "VBTLX": "Total US Bond Market",
    "SCHZ": "Total US Bond Market",
    "FXNAX": "Total US Bond Market",
    # NASDAQ 100
    "QQQ": "NASDAQ 100",
    "QQQM": "NASDAQ 100",
    # S&P 500 Growth
    "VOOG": "S&P 500 Growth",
    "IVW": "S&P 500 Growth",
    "SPYG": "S&P 500 Growth",
    # S&P 500 Value
    "VOOV": "S&P 500 Value",
    "IVE": "S&P 500 Value",
    "SPYV": "S&P 500 Value",
    # Small Cap US
    "VB": "US Small Cap",
    "IJR": "US Small Cap",
    "SCHA": "US Small Cap",
    "VTWO": "US Small Cap (Russell 2000)",
    "IWM": "US Small Cap (Russell 2000)",
    # Mid Cap US
    "VO": "US Mid Cap",
    "IJH": "US Mid Cap",
    "SCHM": "US Mid Cap",
    # TIPS
    "TIP": "US TIPS (Inflation-Protected)",
    "SCHP": "US TIPS (Inflation-Protected)",
    "VTIP": "US TIPS (Inflation-Protected)",
    # Real Estate / REITs
    "VNQ": "US Real Estate (REITs)",
    "SCHH": "US Real Estate (REITs)",
    "IYR": "US Real Estate (REITs)",
    "VGSLX": "US Real Estate (REITs)",
    # International Bond
    "BNDX": "International Bond",
    "IAGG": "International Bond",
    # Dividend
    "VYM": "US High Dividend Yield",
    "SCHD": "US High Dividend Yield",
    "HDV": "US High Dividend Yield",
    # Target-Date (Vanguard examples)
    "VFIFX": "Target Date 2050",
    "VFFVX": "Target Date 2055",
    "VTHRX": "Target Date 2030",
    "VFORX": "Target Date 2040",
}


# Maps high-fee funds/ETFs to low-cost alternatives
LOW_COST_ALTERNATIVES: dict[str, tuple[str, float]] = {
    # (alternative_ticker, alternative_expense_ratio)
    "ARKK": ("VTI", 0.0003),
    "ARKW": ("QQQ", 0.0020),
    "ARKF": ("VGT", 0.0010),
    "ARKG": ("XBI", 0.0035),
    "ARKQ": ("ROBO", 0.0049),
    "AIVSX": ("VOO", 0.0003),
    "AGTHX": ("VTI", 0.0003),
    "FCNTX": ("VOO", 0.0003),
    "AMCPX": ("VTI", 0.0003),
    "ANCFX": ("VTI", 0.0003),
    "ANWPX": ("VXUS", 0.0007),
    "CWGIX": ("VXUS", 0.0007),
    "FDGRX": ("QQQ", 0.0020),
    "TRBCX": ("VUG", 0.0004),
    "VGHCX": ("XLV", 0.0010),
    "PRHSX": ("XLV", 0.0010),
    "RERGX": ("VNQ", 0.0012),
    "FSPHX": ("XLV", 0.0010),
    "FSPTX": ("VGT", 0.0010),
    "NASDX": ("QQQ", 0.0020),
    "DODGX": ("VTV", 0.0004),
    "PRWCX": ("VBIAX", 0.0007),
    "VWELX": ("VBIAX", 0.0007),
    "JAGTX": ("VTI", 0.0003),
    "JMIGX": ("VXUS", 0.0007),
    "PIMIX": ("BND", 0.0003),
    "PTTRX": ("BND", 0.0003),
    "MSFBX": ("VOO", 0.0003),
    "GQEFX": ("VOO", 0.0003),
    "TRCVX": ("VTV", 0.0004),
    "LMVTX": ("VTV", 0.0004),
}


def _compute_fee_drag_projection(
    portfolio_value: float, weighted_er: float, years_list: list[int]
) -> FeeDragProjection:
    """Compute compound growth with and without fees over given year horizons.

    Assumes 7% nominal annual return.
    """
    annual_return = 0.07
    with_fees: list[float] = []
    without_fees: list[float] = []
    fee_cost: list[float] = []

    for y in years_list:
        value_no_fees = portfolio_value * ((1 + annual_return) ** y)
        value_with_fees = portfolio_value * ((1 + annual_return - weighted_er) ** y)
        with_fees.append(round(value_with_fees, 2))
        without_fees.append(round(value_no_fees, 2))
        fee_cost.append(round(value_no_fees - value_with_fees, 2))

    return FeeDragProjection(
        years=years_list,
        with_fees=with_fees,
        without_fees=without_fees,
        fee_cost=fee_cost,
    )


async def _get_holdings_for_user(
    db: AsyncSession,
    current_user: User,
    user_id: Optional[UUID],
) -> list:
    """Shared helper to fetch investment holdings for fee analysis endpoints."""
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    investment_account_ids = [
        acc.id for acc in accounts if acc.account_type in INVESTMENT_ACCOUNT_TYPES
    ]

    if not investment_account_ids:
        return []

    result = await db.execute(
        select(Holding).where(Holding.account_id.in_(investment_account_ids)).limit(10000)
    )
    return list(result.scalars().all())


@router.get("/fee-analysis", response_model=FeeAnalysisResponse)
async def get_fee_analysis(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze portfolio fee impact with projections and low-cost alternatives.

    Returns:
    - Weighted average expense ratio
    - Fee drag projections over 5/10/20/30 years (7% assumed return)
    - High-fee holdings (expense ratio > 0.5%)
    - Low-cost alternative suggestions
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Fee analysis request from user {current_user.id}, filter user_id={user_id}")

    # Check cache
    cache_key = f"fee-analysis:{current_user.organization_id}:{user_id or 'household'}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    holdings = await _get_holdings_for_user(db, current_user, user_id)

    # Aggregate by ticker (same as portfolio summary)
    ticker_data: dict[str, dict] = {}
    for h in holdings:
        val = float(h.current_total_value or 0)
        er = float(h.expense_ratio or 0)
        if h.ticker not in ticker_data:
            ticker_data[h.ticker] = {
                "name": h.name,
                "value": 0.0,
                "expense_ratio": er,
            }
        ticker_data[h.ticker]["value"] += val
        # Keep highest ER across duplicate rows for same ticker
        if er > ticker_data[h.ticker]["expense_ratio"]:
            ticker_data[h.ticker]["expense_ratio"] = er

    portfolio_value = sum(d["value"] for d in ticker_data.values())
    if portfolio_value <= 0:
        empty_projection = FeeDragProjection(
            years=[5, 10, 20, 30],
            with_fees=[0, 0, 0, 0],
            without_fees=[0, 0, 0, 0],
            fee_cost=[0, 0, 0, 0],
        )
        result = FeeAnalysisResponse(
            current_portfolio_value=0,
            weighted_avg_expense_ratio=0,
            total_annual_fees=0,
            fee_drag_projection=empty_projection,
            high_fee_holdings=[],
            low_cost_alternatives=[],
        )
        await cache_setex(cache_key, result, 300)
        return result

    # Calculate weighted average ER
    weighted_er_sum = sum(d["value"] * d["expense_ratio"] for d in ticker_data.values())
    weighted_avg_er = weighted_er_sum / portfolio_value
    total_annual_fees = weighted_er_sum  # value * ER = annual fee

    # Fee drag projection
    projection = _compute_fee_drag_projection(portfolio_value, weighted_avg_er, [5, 10, 20, 30])

    # High-fee holdings (ER > 0.5% = 0.005)
    HIGH_FEE_THRESHOLD = 0.005
    high_fee_holdings = []
    for ticker, data in ticker_data.items():
        if data["expense_ratio"] > HIGH_FEE_THRESHOLD:
            high_fee_holdings.append(
                HighFeeHolding(
                    ticker=ticker,
                    name=data["name"],
                    expense_ratio=round(data["expense_ratio"], 4),
                    annual_fee=round(data["value"] * data["expense_ratio"], 2),
                    value=round(data["value"], 2),
                )
            )
    high_fee_holdings.sort(key=lambda x: x.expense_ratio, reverse=True)

    # Low-cost alternatives
    alternatives = []
    for ticker, data in ticker_data.items():
        if ticker.upper() in LOW_COST_ALTERNATIVES and data["expense_ratio"] > 0.001:
            alt_ticker, alt_er = LOW_COST_ALTERNATIVES[ticker.upper()]
            annual_savings = data["value"] * (data["expense_ratio"] - alt_er)
            if annual_savings > 0:
                alternatives.append(
                    LowCostAlternative(
                        original=ticker,
                        original_er=round(data["expense_ratio"], 4),
                        alternative=alt_ticker,
                        alternative_er=alt_er,
                        annual_savings=round(annual_savings, 2),
                    )
                )
    alternatives.sort(key=lambda x: x.annual_savings, reverse=True)

    result = FeeAnalysisResponse(
        current_portfolio_value=round(portfolio_value, 2),
        weighted_avg_expense_ratio=round(weighted_avg_er, 6),
        total_annual_fees=round(total_annual_fees, 2),
        fee_drag_projection=projection,
        high_fee_holdings=high_fee_holdings,
        low_cost_alternatives=alternatives,
    )

    await cache_setex(cache_key, result, 300)
    return result


@router.get("/fund-overlap", response_model=FundOverlapResponse)
async def get_fund_overlap(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect overlapping fund holdings that track the same index or category.

    Returns groups of holdings that represent redundant exposure to the same
    market index (e.g., SPY + VOO both track S&P 500).
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Fund overlap request from user {current_user.id}, filter user_id={user_id}")

    # Check cache
    cache_key = f"fund-overlap:{current_user.organization_id}:{user_id or 'household'}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    holdings = await _get_holdings_for_user(db, current_user, user_id)

    # Build ticker → value map
    ticker_values: dict[str, float] = {}
    for h in holdings:
        val = float(h.current_total_value or 0)
        ticker_upper = h.ticker.upper() if h.ticker else ""
        if ticker_upper:
            ticker_values[ticker_upper] = ticker_values.get(ticker_upper, 0) + val

    # Group user's holdings by index category
    category_holdings: dict[str, list[str]] = {}
    category_values: dict[str, float] = {}
    for ticker, val in ticker_values.items():
        category = FUND_INDEX_MAP.get(ticker)
        if category:
            if category not in category_holdings:
                category_holdings[category] = []
                category_values[category] = 0.0
            category_holdings[category].append(ticker)
            category_values[category] += val

    # Only report categories with 2+ holdings (actual overlap)
    overlaps = []
    total_overlap_value = 0.0
    for category, tickers in category_holdings.items():
        if len(tickers) >= 2:
            total_val = category_values[category]
            total_overlap_value += total_val
            overlaps.append(
                OverlapGroup(
                    category=category,
                    holdings=sorted(tickers),
                    total_value=round(total_val, 2),
                    suggestion=(
                        f"Consider consolidating into a single {category} fund "
                        f"to reduce complexity and potentially lower fees"
                    ),
                )
            )

    overlaps.sort(key=lambda x: x.total_value, reverse=True)

    result = FundOverlapResponse(
        overlaps=overlaps,
        total_overlap_value=round(total_overlap_value, 2),
    )

    await cache_setex(cache_key, result, 300)
    return result
