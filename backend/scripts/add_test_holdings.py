"""Add test holdings for test@test.com user's investment accounts."""

import asyncio
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_db
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.holding import Holding


async def add_test_holdings():
    """Add test holdings to investment accounts for test@test.com."""

    await init_db()

    async with AsyncSessionLocal() as db:
        # Find test user
        result = await db.execute(
            select(User).where(User.email == "test@test.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("❌ test@test.com user not found")
            return

        print(f"✅ Found user: {user.email}")

        # Find investment accounts
        result = await db.execute(
            select(Account).where(
                Account.organization_id == user.organization_id,
                Account.account_type.in_([
                    AccountType.BROKERAGE,
                    AccountType.RETIREMENT_401K,
                    AccountType.RETIREMENT_IRA,
                    AccountType.RETIREMENT_ROTH,
                ])
            )
        )
        investment_accounts = result.scalars().all()

        if not investment_accounts:
            print("❌ No investment accounts found. Please connect a bank with Plaid first.")
            return

        print(f"✅ Found {len(investment_accounts)} investment account(s)")

        # Define test holdings (realistic stock data)
        test_holdings = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "shares": Decimal("50.5"),
                "cost_basis_per_share": Decimal("145.30"),
                "current_price_per_share": Decimal("185.24"),
                "asset_type": "stock",
            },
            {
                "ticker": "GOOGL",
                "name": "Alphabet Inc.",
                "shares": Decimal("25.0"),
                "cost_basis_per_share": Decimal("120.50"),
                "current_price_per_share": Decimal("142.65"),
                "asset_type": "stock",
            },
            {
                "ticker": "VTSAX",
                "name": "Vanguard Total Stock Market Index Fund",
                "shares": Decimal("100.25"),
                "cost_basis_per_share": Decimal("95.80"),
                "current_price_per_share": Decimal("118.32"),
                "asset_type": "mutual_fund",
            },
            {
                "ticker": "VTI",
                "name": "Vanguard Total Stock Market ETF",
                "shares": Decimal("75.0"),
                "cost_basis_per_share": Decimal("210.45"),
                "current_price_per_share": Decimal("245.18"),
                "asset_type": "etf",
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corporation",
                "shares": Decimal("30.0"),
                "cost_basis_per_share": Decimal("315.20"),
                "current_price_per_share": Decimal("378.91"),
                "asset_type": "stock",
            },
        ]

        # Add holdings to the first investment account
        account = investment_accounts[0]
        print(f"\n📊 Adding holdings to: {account.name}")

        # Check if holdings already exist
        result = await db.execute(
            select(Holding).where(Holding.account_id == account.id)
        )
        existing_holdings = result.scalars().all()

        if existing_holdings:
            print(f"⚠️  Account already has {len(existing_holdings)} holdings. Deleting them first...")
            for holding in existing_holdings:
                await db.delete(holding)
            await db.commit()

        # Add new holdings
        total_value = Decimal("0")
        total_cost_basis = Decimal("0")

        for holding_data in test_holdings:
            shares = holding_data["shares"]
            cost_per_share = holding_data["cost_basis_per_share"]
            current_price = holding_data["current_price_per_share"]

            total_cost = shares * cost_per_share
            current_value = shares * current_price

            holding = Holding(
                account_id=account.id,
                organization_id=user.organization_id,
                ticker=holding_data["ticker"],
                name=holding_data["name"],
                shares=shares,
                cost_basis_per_share=cost_per_share,
                total_cost_basis=total_cost,
                current_price_per_share=current_price,
                current_total_value=current_value,
                price_as_of=datetime.utcnow(),
                asset_type=holding_data["asset_type"],
            )

            db.add(holding)

            total_value += current_value
            total_cost_basis += total_cost

            gain_loss = current_value - total_cost
            gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0

            print(f"  ✅ {holding_data['ticker']}: {shares} shares @ ${current_price} = ${current_value:.2f} "
                  f"(gain: ${gain_loss:.2f} / {gain_loss_pct:.1f}%)")

        # Update account balance to match total portfolio value
        account.current_balance = total_value
        account.balance_as_of = datetime.utcnow()

        await db.commit()

        print(f"\n💰 Portfolio Summary:")
        print(f"   Total Value: ${total_value:.2f}")
        print(f"   Total Cost Basis: ${total_cost_basis:.2f}")
        print(f"   Total Gain/Loss: ${total_value - total_cost_basis:.2f} ({((total_value - total_cost_basis) / total_cost_basis * 100):.1f}%)")
        print(f"\n✅ Test holdings added successfully!")


if __name__ == "__main__":
    asyncio.run(add_test_holdings())
