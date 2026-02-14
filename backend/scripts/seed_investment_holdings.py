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
        accounts_data = [
            {
                "name": "Vanguard 401(k)",
                "type": AccountType.RETIREMENT_401K,
                "institution": "Vanguard",
                "mask": "3456",
                "balance": Decimal("125000.00"),
                "holdings": [
                    {"ticker": "VTSAX", "name": "Vanguard Total Stock Market Index Fund", "shares": Decimal("500"), "price": Decimal("120.50"), "cost_basis": Decimal("50000")},
                    {"ticker": "VTIAX", "name": "Vanguard Total International Stock Index Fund", "shares": Decimal("300"), "price": Decimal("95.00"), "cost_basis": Decimal("25000")},
                    {"ticker": "VBTLX", "name": "Vanguard Total Bond Market Index Fund", "shares": Decimal("200"), "price": Decimal("105.00"), "cost_basis": Decimal("20000")},
                ],
            },
            {
                "name": "Fidelity Roth IRA",
                "type": AccountType.RETIREMENT_ROTH,
                "institution": "Fidelity",
                "mask": "7890",
                "balance": Decimal("75000.00"),
                "holdings": [
                    {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "shares": Decimal("200"), "price": Decimal("240.00"), "cost_basis": Decimal("40000")},
                    {"ticker": "VXUS", "name": "Vanguard Total International Stock ETF", "shares": Decimal("150"), "price": Decimal("65.00"), "cost_basis": Decimal("8000")},
                    {"ticker": "BND", "name": "Vanguard Total Bond Market ETF", "shares": Decimal("100"), "price": Decimal("78.00"), "cost_basis": Decimal("7000")},
                    {"ticker": "VNQ", "name": "Vanguard Real Estate ETF", "shares": Decimal("50"), "price": Decimal("92.00"), "cost_basis": Decimal("4000")},
                ],
            },
            {
                "name": "Charles Schwab Brokerage",
                "type": AccountType.BROKERAGE,
                "institution": "Charles Schwab",
                "mask": "1122",
                "balance": Decimal("250000.00"),
                "holdings": [
                    {"ticker": "AAPL", "name": "Apple Inc.", "shares": Decimal("100"), "price": Decimal("185.00"), "cost_basis": Decimal("15000")},
                    {"ticker": "MSFT", "name": "Microsoft Corporation", "shares": Decimal("80"), "price": Decimal("380.00"), "cost_basis": Decimal("25000")},
                    {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "shares": Decimal("50"), "price": Decimal("142.00"), "cost_basis": Decimal("6000")},
                    {"ticker": "AMZN", "name": "Amazon.com Inc.", "shares": Decimal("60"), "price": Decimal("178.00"), "cost_basis": Decimal("9000")},
                    {"ticker": "NVDA", "name": "NVIDIA Corporation", "shares": Decimal("40"), "price": Decimal("880.00"), "cost_basis": Decimal("20000")},
                    {"ticker": "TSLA", "name": "Tesla Inc.", "shares": Decimal("30"), "price": Decimal("245.00"), "cost_basis": Decimal("6000")},
                    {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "shares": Decimal("100"), "price": Decimal("500.00"), "cost_basis": Decimal("45000")},
                    {"ticker": "QQQ", "name": "Invesco QQQ Trust", "shares": Decimal("50"), "price": Decimal("450.00"), "cost_basis": Decimal("20000")},
                ],
            },
            {
                "name": "Fidelity HSA",
                "type": AccountType.HSA,
                "institution": "Fidelity",
                "mask": "5544",
                "balance": Decimal("15000.00"),
                "holdings": [
                    {"ticker": "FXAIX", "name": "Fidelity 500 Index Fund", "shares": Decimal("100"), "price": Decimal("150.00"), "cost_basis": Decimal("12000")},
                ],
            },
            {
                "name": "Vanguard Money Market",
                "type": AccountType.BROKERAGE,
                "institution": "Vanguard",
                "mask": "9988",
                "balance": Decimal("50000.00"),
                "holdings": [
                    {"ticker": "VMFXX", "name": "Vanguard Federal Money Market Fund", "shares": Decimal("50000"), "price": Decimal("1.00"), "cost_basis": Decimal("50000")},
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

            # Create holdings
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
                    asset_type="etf" if holding_data["ticker"] in ["VTI", "VXUS", "BND", "VNQ", "SPY", "QQQ"] else "mutual_fund" if holding_data["ticker"].endswith("X") else "stock",
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
