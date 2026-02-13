"""Check database and seed if needed."""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.transaction import Transaction

async def main():
    async with AsyncSessionLocal() as db:
        # Check for test user
        result = await db.execute(
            select(User).where(User.email == "test@test.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("❌ User test@test.com not found!")
            print("Please register with email: test@test.com and password: test")
            return

        print(f"✅ Found user: {user.email}")
        print(f"   Organization: {user.organization_id}")

        # Check transaction count
        result = await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.organization_id == user.organization_id
            )
        )
        count = result.scalar()

        print(f"\n📊 Transactions in database: {count}")

        if count == 0:
            print("\n⚠️  No transactions found! Running seed script...")
            # Import and run seed
            from scripts.seed_mock_data import seed_mock_data
            await seed_mock_data()
        else:
            # Show sample transactions
            result = await db.execute(
                select(Transaction)
                .where(Transaction.organization_id == user.organization_id)
                .limit(5)
            )
            txns = result.scalars().all()
            print("\n📝 Sample transactions:")
            for txn in txns:
                print(f"   {txn.date}: {txn.merchant_name} - ${txn.amount}")

if __name__ == "__main__":
    asyncio.run(main())
