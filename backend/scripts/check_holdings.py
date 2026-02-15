"""Check holdings metadata for test@test.com user."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.holding import Holding


async def check_holdings():
    async with AsyncSessionLocal() as db:
        # Find test user
        result = await db.execute(select(User).where(User.email == "test@test.com"))
        user = result.scalar_one_or_none()

        if not user:
            print("❌ User not found")
            return

        print(f"✅ Found user: {user.email}")
        print(f"   Organization ID: {user.organization_id}\n")

        # Get holdings
        result = await db.execute(
            select(Holding).where(Holding.organization_id == user.organization_id)
        )
        holdings = result.scalars().all()

        print(f"Found {len(holdings)} holdings:\n")

        for h in holdings:
            print(f"Ticker: {h.ticker} ({h.name})")
            print(f"  Shares: {h.shares}")
            print(f"  Price per share: ${h.current_price_per_share}")
            print(f"  Total value: ${h.current_total_value}")
            print(f"  Asset class: {h.asset_class}")
            print(f"  Country: {h.country}")
            print(f"  Market cap: {h.market_cap}")
            print(f"  Sector: {h.sector}")
            print(f"  Industry: {h.industry}")
            print()


if __name__ == "__main__":
    asyncio.run(check_holdings())
