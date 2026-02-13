"""Create comprehensive test portfolio for test@test.com matching Plaid structure."""

import asyncio
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_db
from app.models.user import User
from app.models.account import Account, AccountType, AccountSource
from app.models.holding import Holding


async def create_comprehensive_test_portfolio():
    """Create a comprehensive test portfolio matching Plaid's API structure."""

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

        # Delete existing investment accounts to start fresh
        existing_accounts = await db.execute(
            select(Account).where(
                Account.organization_id == user.organization_id,
                Account.account_type.in_([
                    AccountType.BROKERAGE,
                    AccountType.RETIREMENT_401K,
                    AccountType.RETIREMENT_IRA,
                    AccountType.RETIREMENT_ROTH,
                    AccountType.HSA,
                    AccountType.PROPERTY,
                    AccountType.VEHICLE,
                    AccountType.CRYPTO,
                ])
            )
        )
        for account in existing_accounts.scalars().all():
            await db.delete(account)
        await db.commit()
        print("🗑️  Cleared existing test investment accounts")

        # ============================================================================
        # RETIREMENT ACCOUNTS (Plaid-connected)
        # ============================================================================

        # 1. Traditional 401(k) - Company Match
        print("\n📊 Creating retirement accounts...")
        traditional_401k = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Vanguard 401(k)",
            account_type=AccountType.RETIREMENT_401K,
            account_source=AccountSource.PLAID,
            institution_name="Vanguard",
            mask="1234",
            is_manual=False,
            is_active=True,
        )
        db.add(traditional_401k)
        await db.flush()

        # Holdings for Traditional 401k - Diversified mix
        trad_401k_holdings = [
            {
                "ticker": "VTSAX",
                "name": "Vanguard Total Stock Market Index Fund",
                "shares": Decimal("250.5"),
                "cost_basis_per_share": Decimal("92.50"),
                "current_price_per_share": Decimal("118.32"),
                "asset_type": "mutual_fund",
            },
            {
                "ticker": "VTIAX",
                "name": "Vanguard Total International Stock Index Fund",
                "shares": Decimal("150.25"),
                "cost_basis_per_share": Decimal("24.80"),
                "current_price_per_share": Decimal("32.15"),
                "asset_type": "mutual_fund",
            },
            {
                "ticker": "VBTLX",
                "name": "Vanguard Total Bond Market Index Fund",
                "shares": Decimal("100.0"),
                "cost_basis_per_share": Decimal("10.50"),
                "current_price_per_share": Decimal("10.85"),
                "asset_type": "mutual_fund",
            },
        ]

        # 2. Roth 401(k) - After-tax contributions
        roth_401k = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Fidelity Roth 401(k)",
            account_type=AccountType.RETIREMENT_401K,
            account_source=AccountSource.PLAID,
            institution_name="Fidelity",
            mask="5678",
            is_manual=False,
            is_active=True,
        )
        db.add(roth_401k)
        await db.flush()

        roth_401k_holdings = [
            {
                "ticker": "FXAIX",
                "name": "Fidelity 500 Index Fund",
                "shares": Decimal("120.0"),
                "cost_basis_per_share": Decimal("125.00"),
                "current_price_per_share": Decimal("165.42"),
                "asset_type": "mutual_fund",
            },
            {
                "ticker": "FTIHX",
                "name": "Fidelity Total International Index Fund",
                "shares": Decimal("80.0"),
                "cost_basis_per_share": Decimal("12.50"),
                "current_price_per_share": Decimal("14.28"),
                "asset_type": "mutual_fund",
            },
        ]

        # 3. Traditional IRA
        traditional_ira = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Charles Schwab Traditional IRA",
            account_type=AccountType.RETIREMENT_IRA,
            account_source=AccountSource.PLAID,
            institution_name="Charles Schwab",
            mask="9012",
            is_manual=False,
            is_active=True,
        )
        db.add(traditional_ira)
        await db.flush()

        traditional_ira_holdings = [
            {
                "ticker": "VTI",
                "name": "Vanguard Total Stock Market ETF",
                "shares": Decimal("50.0"),
                "cost_basis_per_share": Decimal("210.00"),
                "current_price_per_share": Decimal("245.18"),
                "asset_type": "etf",
            },
            {
                "ticker": "BND",
                "name": "Vanguard Total Bond Market ETF",
                "shares": Decimal("40.0"),
                "cost_basis_per_share": Decimal("78.50"),
                "current_price_per_share": Decimal("74.25"),
                "asset_type": "etf",
            },
        ]

        # 4. Roth IRA
        roth_ira = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Fidelity Roth IRA",
            account_type=AccountType.RETIREMENT_ROTH,
            account_source=AccountSource.PLAID,
            institution_name="Fidelity",
            mask="3456",
            is_manual=False,
            is_active=True,
        )
        db.add(roth_ira)
        await db.flush()

        roth_ira_holdings = [
            {
                "ticker": "VOO",
                "name": "Vanguard S&P 500 ETF",
                "shares": Decimal("25.0"),
                "cost_basis_per_share": Decimal("380.00"),
                "current_price_per_share": Decimal("465.82"),
                "asset_type": "etf",
            },
            {
                "ticker": "QQQ",
                "name": "Invesco QQQ Trust",
                "shares": Decimal("15.0"),
                "cost_basis_per_share": Decimal("320.00"),
                "current_price_per_share": Decimal("425.65"),
                "asset_type": "etf",
            },
        ]

        # 5. HSA (Health Savings Account)
        hsa = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Fidelity HSA",
            account_type=AccountType.HSA,
            account_source=AccountSource.PLAID,
            institution_name="Fidelity",
            mask="7890",
            is_manual=False,
            is_active=True,
        )
        db.add(hsa)
        await db.flush()

        hsa_holdings = [
            {
                "ticker": "FXAIX",
                "name": "Fidelity 500 Index Fund",
                "shares": Decimal("35.0"),
                "cost_basis_per_share": Decimal("130.00"),
                "current_price_per_share": Decimal("165.42"),
                "asset_type": "mutual_fund",
            },
        ]

        # ============================================================================
        # TAXABLE BROKERAGE ACCOUNTS (Plaid-connected)
        # ============================================================================

        print("\n💰 Creating taxable brokerage accounts...")

        # 6. Primary Brokerage - Growth stocks
        brokerage_1 = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Fidelity Brokerage",
            account_type=AccountType.BROKERAGE,
            account_source=AccountSource.PLAID,
            institution_name="Fidelity",
            mask="2468",
            is_manual=False,
            is_active=True,
        )
        db.add(brokerage_1)
        await db.flush()

        brokerage_1_holdings = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "shares": Decimal("75.0"),
                "cost_basis_per_share": Decimal("145.30"),
                "current_price_per_share": Decimal("185.24"),
                "asset_type": "stock",
            },
            {
                "ticker": "GOOGL",
                "name": "Alphabet Inc.",
                "shares": Decimal("40.0"),
                "cost_basis_per_share": Decimal("120.50"),
                "current_price_per_share": Decimal("142.65"),
                "asset_type": "stock",
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corporation",
                "shares": Decimal("50.0"),
                "cost_basis_per_share": Decimal("315.20"),
                "current_price_per_share": Decimal("378.91"),
                "asset_type": "stock",
            },
            {
                "ticker": "TSLA",
                "name": "Tesla Inc.",
                "shares": Decimal("30.0"),
                "cost_basis_per_share": Decimal("220.00"),
                "current_price_per_share": Decimal("245.50"),
                "asset_type": "stock",
            },
        ]

        # 7. Secondary Brokerage - Index funds and bonds
        brokerage_2 = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Charles Schwab Brokerage",
            account_type=AccountType.BROKERAGE,
            account_source=AccountSource.PLAID,
            institution_name="Charles Schwab",
            mask="1357",
            is_manual=False,
            is_active=True,
        )
        db.add(brokerage_2)
        await db.flush()

        brokerage_2_holdings = [
            {
                "ticker": "VTI",
                "name": "Vanguard Total Stock Market ETF",
                "shares": Decimal("100.0"),
                "cost_basis_per_share": Decimal("220.00"),
                "current_price_per_share": Decimal("245.18"),
                "asset_type": "etf",
            },
            {
                "ticker": "VXUS",
                "name": "Vanguard Total International Stock ETF",
                "shares": Decimal("80.0"),
                "cost_basis_per_share": Decimal("58.00"),
                "current_price_per_share": Decimal("62.45"),
                "asset_type": "etf",
            },
            {
                "ticker": "AGG",
                "name": "iShares Core U.S. Aggregate Bond ETF",
                "shares": Decimal("50.0"),
                "cost_basis_per_share": Decimal("104.50"),
                "current_price_per_share": Decimal("102.85"),
                "asset_type": "etf",
            },
        ]

        # 8. Money Market Account (within brokerage but cash equivalent)
        money_market = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Vanguard Money Market",
            account_type=AccountType.BROKERAGE,
            account_source=AccountSource.PLAID,
            institution_name="Vanguard",
            mask="9876",
            is_manual=False,
            is_active=True,
            current_balance=Decimal("15000.00"),
            balance_as_of=datetime.utcnow(),
        )
        db.add(money_market)
        await db.flush()

        money_market_holdings = [
            {
                "ticker": "VMFXX",
                "name": "Vanguard Federal Money Market Fund",
                "shares": Decimal("15000.0"),
                "cost_basis_per_share": Decimal("1.00"),
                "current_price_per_share": Decimal("1.00"),
                "asset_type": "mutual_fund",
            },
        ]

        # ============================================================================
        # MANUAL ACCOUNTS (Not supported by Plaid)
        # ============================================================================

        print("\n🏠 Creating manual accounts...")

        # 9. Property - Primary Residence
        property_account = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Primary Residence - 123 Main St",
            account_type=AccountType.PROPERTY,
            account_source=AccountSource.MANUAL,
            institution_name="Zillow Estimate",
            is_manual=True,
            is_active=True,
            current_balance=Decimal("450000.00"),
            balance_as_of=datetime.utcnow(),
        )
        db.add(property_account)

        # 10. Vehicle
        vehicle_account = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="2022 Tesla Model 3",
            account_type=AccountType.VEHICLE,
            account_source=AccountSource.MANUAL,
            institution_name="KBB Value",
            is_manual=True,
            is_active=True,
            current_balance=Decimal("38500.00"),
            balance_as_of=datetime.utcnow(),
        )
        db.add(vehicle_account)

        # 11. Cryptocurrency (Manual tracking)
        crypto_account = Account(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Coinbase Crypto",
            account_type=AccountType.CRYPTO,
            account_source=AccountSource.MANUAL,
            institution_name="Coinbase",
            mask="4321",
            is_manual=True,
            is_active=True,
        )
        db.add(crypto_account)
        await db.flush()

        crypto_holdings = [
            {
                "ticker": "BTC",
                "name": "Bitcoin",
                "shares": Decimal("0.5"),
                "cost_basis_per_share": Decimal("42000.00"),
                "current_price_per_share": Decimal("65000.00"),
                "asset_type": "crypto",
            },
            {
                "ticker": "ETH",
                "name": "Ethereum",
                "shares": Decimal("5.0"),
                "cost_basis_per_share": Decimal("2200.00"),
                "current_price_per_share": Decimal("3400.00"),
                "asset_type": "crypto",
            },
        ]

        # ============================================================================
        # ADD ALL HOLDINGS
        # ============================================================================

        print("\n📈 Adding holdings...")

        all_holdings_data = [
            (traditional_401k.id, trad_401k_holdings, "Traditional 401(k)"),
            (roth_401k.id, roth_401k_holdings, "Roth 401(k)"),
            (traditional_ira.id, traditional_ira_holdings, "Traditional IRA"),
            (roth_ira.id, roth_ira_holdings, "Roth IRA"),
            (hsa.id, hsa_holdings, "HSA"),
            (brokerage_1.id, brokerage_1_holdings, "Primary Brokerage"),
            (brokerage_2.id, brokerage_2_holdings, "Secondary Brokerage"),
            (money_market.id, money_market_holdings, "Money Market"),
            (crypto_account.id, crypto_holdings, "Crypto"),
        ]

        total_portfolio_value = Decimal("0")
        total_cost_basis = Decimal("0")

        for account_id, holdings_list, account_name in all_holdings_data:
            account_value = Decimal("0")
            account_cost = Decimal("0")

            for holding_data in holdings_list:
                shares = holding_data["shares"]
                cost_per_share = holding_data["cost_basis_per_share"]
                current_price = holding_data["current_price_per_share"]

                total_cost = shares * cost_per_share
                current_value = shares * current_price

                holding = Holding(
                    account_id=account_id,
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

                account_value += current_value
                account_cost += total_cost

                gain_loss = current_value - total_cost
                gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0

                print(f"  ✅ {account_name}: {holding_data['ticker']} - {shares} shares @ ${current_price} = ${current_value:.2f} (gain: ${gain_loss:.2f} / {gain_loss_pct:.1f}%)")

            total_portfolio_value += account_value
            total_cost_basis += account_cost

            # Update account balance
            account_result = await db.execute(
                select(Account).where(Account.id == account_id)
            )
            account = account_result.scalar_one()
            account.current_balance = account_value
            account.balance_as_of = datetime.utcnow()

        # Add property and vehicle to total
        total_portfolio_value += property_account.current_balance + vehicle_account.current_balance

        await db.commit()

        # ============================================================================
        # SUMMARY
        # ============================================================================

        print(f"\n💰 Portfolio Summary:")
        print(f"   Investment Accounts Total: ${total_portfolio_value - property_account.current_balance - vehicle_account.current_balance:.2f}")
        print(f"   Property Value: ${property_account.current_balance:.2f}")
        print(f"   Vehicle Value: ${vehicle_account.current_balance:.2f}")
        print(f"   ─────────────────────────")
        print(f"   Total Portfolio Value: ${total_portfolio_value:.2f}")
        print(f"   Total Cost Basis: ${total_cost_basis:.2f}")
        print(f"   Total Gain/Loss: ${total_portfolio_value - total_cost_basis - property_account.current_balance - vehicle_account.current_balance:.2f} ({((total_portfolio_value - total_cost_basis - property_account.current_balance - vehicle_account.current_balance) / total_cost_basis * 100):.1f}%)")
        print(f"\n✅ Comprehensive test portfolio created successfully!")
        print(f"\n🎯 Account Breakdown:")
        print(f"   - 2x 401(k) accounts (Traditional + Roth)")
        print(f"   - 2x IRA accounts (Traditional + Roth)")
        print(f"   - 1x HSA")
        print(f"   - 2x Taxable Brokerage")
        print(f"   - 1x Money Market")
        print(f"   - 1x Crypto")
        print(f"   - 1x Property")
        print(f"   - 1x Vehicle")
        print(f"\n🎯 Now visit /investments to see your comprehensive portfolio!")


if __name__ == "__main__":
    asyncio.run(create_comprehensive_test_portfolio())
