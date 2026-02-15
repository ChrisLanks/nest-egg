"""Delete existing investment accounts and holdings for test@test.com, then re-seed."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.holding import Holding


async def reset_investments():
    """Delete existing investment accounts and holdings for test@test.com."""
    async with AsyncSessionLocal() as db:
        # Find test user
        result = await db.execute(select(User).where(User.email == "test@test.com"))
        user = result.scalar_one_or_none()

        if not user:
            print("❌ User test@test.com not found")
            return

        print(f"✅ Found user: {user.email}")
        print(f"   Organization ID: {user.organization_id}\n")

        # Delete existing holdings
        result = await db.execute(
            delete(Holding).where(Holding.organization_id == user.organization_id)
        )
        holdings_deleted = result.rowcount
        print(f"🗑️  Deleted {holdings_deleted} holdings")

        # Delete investment accounts (not checking/credit/etc)
        investment_types = [
            AccountType.RETIREMENT_401K,
            AccountType.RETIREMENT_ROTH,
            AccountType.RETIREMENT_TRADITIONAL,
            AccountType.RETIREMENT_SEP,
            AccountType.RETIREMENT_SIMPLE,
            AccountType.RETIREMENT_PENSION,
            AccountType.BROKERAGE,
            AccountType.HSA,
        ]

        result = await db.execute(
            delete(Account).where(
                Account.organization_id == user.organization_id,
                Account.account_type.in_(investment_types),
            )
        )
        accounts_deleted = result.rowcount
        print(f"🗑️  Deleted {accounts_deleted} investment accounts")

        await db.commit()
        print("\n✅ Cleanup complete! Now run the seed script:")
        print("   python backend/scripts/seed_investment_holdings.py")


if __name__ == "__main__":
    asyncio.run(reset_investments())
