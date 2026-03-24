"""One-shot dev setup: create test@test.com and seed all mock data.

Usage
-----
    python scripts/setup_dev_user.py

Creates (idempotent — safe to run multiple times):
  - Organisation "Test Household"
  - User test@test.com / password: test
    - birthdate: 1985-06-15 (age ~40, so net worth benchmark insight fires)
    - email_verified: True, is_org_admin: True
  - All mock transaction/account/holding data via seed_mock_data internals
  - Investment holdings (triggers fund-fee and concentration insights)
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.crud.user import organization_crud
from app.models.user import Organization, User


async def main():
    async with AsyncSessionLocal() as db:
        # ── Check / create user ──────────────────────────────────────────
        result = await db.execute(select(User).where(User.email == "test@test.com"))
        user = result.scalar_one_or_none()

        if user:
            print(f"✅ User test@test.com already exists (id={user.id})")
        else:
            print("👤 Creating test@test.com …")

            org = await organization_crud.create(db, name="Test Household")

            user = User(
                email="test@test.com",
                password_hash=hash_password("test"),
                organization_id=org.id,
                is_org_admin=True,
                email_verified=True,
                birthdate=date(1985, 6, 15),  # age ~40 → net worth benchmark fires
                onboarding_completed=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"   ✓ Created user id={user.id}, org={org.id}")

        # ── Seed mock transactions / accounts ────────────────────────────
        from app.models.transaction import Transaction
        from sqlalchemy import func

        tx_count_result = await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.organization_id == user.organization_id
            )
        )
        tx_count = tx_count_result.scalar()

        if tx_count > 0:
            print(f"✅ Already have {tx_count} transactions — skipping transaction seed")
        else:
            print("🌱 Seeding mock transactions and accounts …")
            from app.api.v1.dev import seed_mock_data_internal
            await seed_mock_data_internal(db, user)
            await db.commit()
            tx_count_result = await db.execute(
                select(func.count(Transaction.id)).where(
                    Transaction.organization_id == user.organization_id
                )
            )
            print(f"   ✓ Seeded {tx_count_result.scalar()} transactions")

        # ── Seed investment holdings ──────────────────────────────────────
        from app.models.holding import Holding
        from app.models.account import Account

        holding_count_result = await db.execute(
            select(func.count(Holding.id))
            .join(Account, Holding.account_id == Account.id)
            .where(Account.organization_id == user.organization_id)
        )
        holding_count = holding_count_result.scalar()

        if holding_count > 0:
            print(f"✅ Already have {holding_count} holdings — skipping holdings seed")
        else:
            print("📈 Seeding investment holdings …")
            try:
                # Import and run the investment holdings seeder
                from scripts.seed_investment_holdings import seed_investment_holdings
                await seed_investment_holdings()
                holding_count_result = await db.execute(
                    select(func.count(Holding.id))
                    .join(Account, Holding.account_id == Account.id)
                    .where(Account.organization_id == user.organization_id)
                )
                print(f"   ✓ Seeded {holding_count_result.scalar()} holdings")
            except Exception as e:
                print(f"   ⚠️  Holdings seed failed (non-fatal): {e}")

        print("\n🎉 Dev setup complete!")
        print("   Email:    test@test.com")
        print("   Password: test")
        print("   Birthdate: 1985-06-15 (age ~40 → net worth benchmark insight will fire)")
        print("\n   Start the backend:  ./start.sh")
        print("   Start the frontend: cd ../frontend && npm run dev")


if __name__ == "__main__":
    asyncio.run(main())
