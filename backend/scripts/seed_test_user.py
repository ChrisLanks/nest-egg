"""Automatically seed test user with mock data on startup if needed."""
import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.transaction import Transaction


async def seed_test_user_if_needed():
    """Check if test@test.com exists and has data, seed if not."""
    async with AsyncSessionLocal() as db:
        # Check for test user
        result = await db.execute(
            select(User).where(User.email == "test@test.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("ℹ️  test@test.com user not found, skipping auto-seed")
            return

        # Check transaction count
        result = await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.organization_id == user.organization_id
            )
        )
        count = result.scalar()

        if count > 0:
            print(f"✅ test@test.com already has {count} transactions")
            return

        print("🌱 Auto-seeding test@test.com with mock data...")

        # Import the seed function
        from app.api.v1.dev import seed_mock_data_internal

        await seed_mock_data_internal(db, user)
        await db.commit()

        print("✅ Test data seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_test_user_if_needed())
