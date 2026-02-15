"""Seed investment accounts and holdings for test@test.com user."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import uuid

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.account import Account, AccountType, AccountSource
from app.models.holding import Holding


async def seed_investment_holdings():
    """Seed mock investment holdings for test@test.com user."""
    async with AsyncSessionLocal() as db:
        # Find the test user
        result = await db.execute(
            select(User).where(User.email == "test@test.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("❌ User test@test.com not found. Please register first.")
            return

        print(f"✅ Found user: {user.email}")
        print(f"   Organization ID: {user.organization_id}\n")

        # Create investment accounts with holdings
        # Holdings include Alpha Vantage-style metadata for accurate style box classification
        accounts_data = [
            {
                "name": "Vanguard 401(k)",
                "type": AccountType.RETIREMENT_401K,
                "institution": "Vanguard",
                "mask": "3456",
                "balance": Decimal("125000.00"),
                "holdings": [
                    {"ticker": "VTSAX", "name": "Vanguard Total Stock Market Index Fund", "shares": Decimal("500"), "price": Decimal("120.50"), "cost_basis": Decimal("50000"),
                     "asset_type": "mutual_fund", "asset_class": "domestic", "market_cap": "large", "sector": "Diversified", "industry": "Index Fund", "country": "USA", "expense_ratio": Decimal("0.0004")},
                    {"ticker": "VTIAX", "name": "Vanguard Total International Stock Index Fund", "shares": Decimal("300"), "price": Decimal("95.00"), "cost_basis": Decimal("25000"),
                     "asset_type": "mutual_fund", "asset_class": "international", "market_cap": "large", "sector": "Diversified", "industry": "Index Fund", "country": "Global", "expense_ratio": Decimal("0.0005")},
                    {"ticker": "VBTLX", "name": "Vanguard Total Bond Market Index Fund", "shares": Decimal("200"), "price": Decimal("105.00"), "cost_basis": Decimal("20000"),
                     "asset_type": "mutual_fund", "asset_class": "bond", "market_cap": None, "sector": "Fixed Income", "industry": "Bond Fund", "country": "USA", "expense_ratio": Decimal("0.0005")},
                ],
            },
            {
                "name": "Fidelity Roth IRA",
                "type": AccountType.RETIREMENT_ROTH,
                "institution": "Fidelity",
                "mask": "7890",
                "balance": Decimal("75000.00"),
                "holdings": [
                    {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "shares": Decimal("200"), "price": Decimal("240.00"), "cost_basis": Decimal("40000"),
                     "asset_type": "etf", "asset_class": "domestic", "market_cap": "large", "sector": "Diversified", "industry": "Index ETF", "country": "USA", "expense_ratio": Decimal("0.0003")},
                    {"ticker": "VXUS", "name": "Vanguard Total International Stock ETF", "shares": Decimal("150"), "price": Decimal("65.00"), "cost_basis": Decimal("8000"),
                     "asset_type": "etf", "asset_class": "international", "market_cap": "large", "sector": "Diversified", "industry": "Index ETF", "country": "Global", "expense_ratio": Decimal("0.0004")},
                    {"ticker": "BND", "name": "Vanguard Total Bond Market ETF", "shares": Decimal("100"), "price": Decimal("78.00"), "cost_basis": Decimal("7000"),
                     "asset_type": "etf", "asset_class": "bond", "market_cap": None, "sector": "Fixed Income", "industry": "Bond ETF", "country": "USA", "expense_ratio": Decimal("0.0003")},
                    {"ticker": "VNQ", "name": "Vanguard Real Estate ETF", "shares": Decimal("50"), "price": Decimal("92.00"), "cost_basis": Decimal("4000"),
                     "asset_type": "etf", "asset_class": "domestic", "market_cap": "large", "sector": "Real Estate", "industry": "REIT", "country": "USA", "expense_ratio": Decimal("0.0012")},
                ],
            },
            {
                "name": "Charles Schwab Brokerage",
                "type": AccountType.BROKERAGE,
                "institution": "Charles Schwab",
                "mask": "1122",
                "balance": Decimal("260000.00"),  # Updated to account for international stocks
                "holdings": [
                    {"ticker": "AAPL", "name": "Apple Inc.", "shares": Decimal("100"), "price": Decimal("185.00"), "cost_basis": Decimal("15000"),
                     "asset_type": "stock", "asset_class": "domestic", "market_cap": "large", "sector": "Technology", "industry": "Consumer Electronics", "country": "USA", "expense_ratio": None},
                    {"ticker": "MSFT", "name": "Microsoft Corporation", "shares": Decimal("80"), "price": Decimal("380.00"), "cost_basis": Decimal("25000"),
                     "asset_type": "stock", "asset_class": "domestic", "market_cap": "large", "sector": "Technology", "industry": "Software", "country": "USA", "expense_ratio": None},
                    {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "shares": Decimal("50"), "price": Decimal("142.00"), "cost_basis": Decimal("6000"),
                     "asset_type": "stock", "asset_class": "domestic", "market_cap": "large", "sector": "Technology", "industry": "Internet Services", "country": "USA", "expense_ratio": None},
                    {"ticker": "AMZN", "name": "Amazon.com Inc.", "shares": Decimal("60"), "price": Decimal("178.00"), "cost_basis": Decimal("9000"),
                     "asset_type": "stock", "asset_class": "domestic", "market_cap": "large", "sector": "Consumer Cyclical", "industry": "E-commerce", "country": "USA", "expense_ratio": None},
                    {"ticker": "NVDA", "name": "NVIDIA Corporation", "shares": Decimal("40"), "price": Decimal("880.00"), "cost_basis": Decimal("20000"),
                     "asset_type": "stock", "asset_class": "domestic", "market_cap": "large", "sector": "Technology", "industry": "Semiconductors", "country": "USA", "expense_ratio": None},
                    {"ticker": "TSLA", "name": "Tesla Inc.", "shares": Decimal("30"), "price": Decimal("245.00"), "cost_basis": Decimal("6000"),
                     "asset_type": "stock", "asset_class": "domestic", "market_cap": "large", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers", "country": "USA", "expense_ratio": None},
                    {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "shares": Decimal("100"), "price": Decimal("500.00"), "cost_basis": Decimal("45000"),
                     "asset_type": "etf", "asset_class": "domestic", "market_cap": "large", "sector": "Diversified", "industry": "Index ETF", "country": "USA", "expense_ratio": Decimal("0.0009")},
                    {"ticker": "QQQ", "name": "Invesco QQQ Trust", "shares": Decimal("50"), "price": Decimal("450.00"), "cost_basis": Decimal("20000"),
                     "asset_type": "etf", "asset_class": "domestic", "market_cap": "large", "sector": "Technology", "industry": "Tech-Heavy ETF", "country": "USA", "expense_ratio": Decimal("0.0020")},
                    # International stocks for realistic breakdown
                    {"ticker": "TSM", "name": "Taiwan Semiconductor Manufacturing", "shares": Decimal("25"), "price": Decimal("145.00"), "cost_basis": Decimal("3000"),
                     "asset_type": "stock", "asset_class": "international", "market_cap": "large", "sector": "Technology", "industry": "Semiconductors", "country": "Taiwan", "expense_ratio": None},
                    {"ticker": "SAP", "name": "SAP SE ADR", "shares": Decimal("15"), "price": Decimal("180.00"), "cost_basis": Decimal("2500"),
                     "asset_type": "stock", "asset_class": "international", "market_cap": "large", "sector": "Technology", "industry": "Software", "country": "Germany", "expense_ratio": None},
                    {"ticker": "BABA", "name": "Alibaba Group Holding Ltd ADR", "shares": Decimal("40"), "price": Decimal("85.00"), "cost_basis": Decimal("5000"),
                     "asset_type": "stock", "asset_class": "international", "market_cap": "large", "sector": "Consumer Cyclical", "industry": "E-commerce", "country": "China", "expense_ratio": None},
                ],
            },
            {
                "name": "Fidelity HSA",
                "type": AccountType.HSA,
                "institution": "Fidelity",
                "mask": "5544",
                "balance": Decimal("15000.00"),
                "holdings": [
                    {"ticker": "FXAIX", "name": "Fidelity 500 Index Fund", "shares": Decimal("100"), "price": Decimal("150.00"), "cost_basis": Decimal("12000"),
                     "asset_type": "mutual_fund", "asset_class": "domestic", "market_cap": "large", "sector": "Diversified", "industry": "Index Fund", "country": "USA", "expense_ratio": Decimal("0.0002")},
                ],
            },
            {
                "name": "Vanguard Money Market",
                "type": AccountType.BROKERAGE,
                "institution": "Vanguard",
                "mask": "9988",
                "balance": Decimal("50000.00"),
                "holdings": [
                    {"ticker": "VMFXX", "name": "Vanguard Federal Money Market Fund", "shares": Decimal("50000"), "price": Decimal("1.00"), "cost_basis": Decimal("50000"),
                     "asset_type": "mutual_fund", "asset_class": "cash", "market_cap": None, "sector": "Money Market", "industry": "Cash Equivalent", "country": "USA", "expense_ratio": Decimal("0.0011")},
                ],
            },
        ]

        total_accounts = 0
        total_holdings = 0

        for account_data in accounts_data:
            # Create account
            account = Account(
                id=uuid.uuid4(),
                organization_id=user.organization_id,
                user_id=user.id,
                name=account_data["name"],
                account_type=account_data["type"],
                account_source=AccountSource.MANUAL,
                institution_name=account_data["institution"],
                mask=account_data["mask"],
                current_balance=account_data["balance"],
                balance_as_of=datetime.utcnow(),
                is_active=True,
                is_manual=True,
            )
            db.add(account)
            await db.flush()
            total_accounts += 1
            print(f"✅ Created account: {account.name} (****{account.mask})")

            # Create holdings with Alpha Vantage-style metadata
            for holding_data in account_data["holdings"]:
                holding = Holding(
                    id=uuid.uuid4(),
                    organization_id=user.organization_id,
                    account_id=account.id,
                    ticker=holding_data["ticker"],
                    name=holding_data["name"],
                    shares=holding_data["shares"],
                    current_price_per_share=holding_data["price"],
                    current_total_value=holding_data["shares"] * holding_data["price"],
                    price_as_of=datetime.utcnow(),
                    total_cost_basis=holding_data["cost_basis"],
                    cost_basis_per_share=holding_data["cost_basis"] / holding_data["shares"] if holding_data["shares"] > 0 else Decimal("0"),
                    # Alpha Vantage-style metadata for accurate classification
                    asset_type=holding_data.get("asset_type"),
                    asset_class=holding_data.get("asset_class"),
                    market_cap=holding_data.get("market_cap"),
                    sector=holding_data.get("sector"),
                    industry=holding_data.get("industry"),
                    country=holding_data.get("country"),
                    expense_ratio=holding_data.get("expense_ratio"),
                )
                db.add(holding)
                total_holdings += 1

            print(f"   ↳ Added {len(account_data['holdings'])} holdings\n")

        await db.commit()

        print(f"🎉 Successfully created:")
        print(f"   • {total_accounts} investment accounts")
        print(f"   • {total_holdings} holdings")
        print(f"\n💡 Refresh the Investments page to see the treemap!")


if __name__ == "__main__":
    print("🌱 Seeding investment holdings...\n")
    asyncio.run(seed_investment_holdings())
