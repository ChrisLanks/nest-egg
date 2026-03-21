"""Create a test investment account with holdings for test@test.com."""

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db
from app.models.account import Account, AccountSource, AccountType
from app.models.holding import Holding
from app.models.user import User


async def create_test_investment_account():
    """Create a test investment account with holdings."""

    await init_db()

    async with AsyncSessionLocal() as db:
        # Find test user
        result = await db.execute(select(User).where(User.email == "test@test.com"))
        user = result.scalar_one_or_none()

        if not user:
            print("❌ test@test.com user not found")
            return

        print(f"✅ Found user: {user.email}")

        # Create investment account
        account = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Fidelity Brokerage",
            account_type=AccountType.BROKERAGE,
            account_source=AccountSource.MANUAL,
            institution_name="Fidelity",
            mask="7890",
            is_manual=True,
            is_active=True,
        )
        db.add(account)
        await db.flush()  # Get account.id

        print(f"✅ Created investment account: {account.name}")

        # Define test holdings
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

        print(f"\n📊 Adding {len(test_holdings)} holdings...")

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
                price_as_of=datetime.now(timezone.utc).replace(tzinfo=None),
                asset_type=holding_data["asset_type"],
            )

            db.add(holding)

            total_value += current_value
            total_cost_basis += total_cost

            gain_loss = current_value - total_cost
            gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0

            ticker = holding_data["ticker"]
            print(
                f"  ✅ {ticker}: {shares} shares"
                f" @ ${current_price} = ${current_value:.2f}"
                f" (gain: ${gain_loss:.2f} / {gain_loss_pct:.1f}%)"
            )

        # Set account balance to total portfolio value
        account.current_balance = total_value
        account.balance_as_of = datetime.now(timezone.utc).replace(tzinfo=None)

        await db.commit()

        print("\n💰 Portfolio Summary:")
        print(f"   Total Value: ${total_value:.2f}")
        print(f"   Total Cost Basis: ${total_cost_basis:.2f}")
        gl = total_value - total_cost_basis
        gl_pct = (gl / total_cost_basis * 100) if total_cost_basis > 0 else 0
        print(f"   Total Gain/Loss: ${gl:.2f} ({gl_pct:.1f}%)")
        print("\n✅ Test investment account created successfully!")
        print("\n🎯 Now visit /investments to see your portfolio!")


if __name__ == "__main__":
    asyncio.run(create_test_investment_account())
