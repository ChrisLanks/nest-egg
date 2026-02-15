"""Seed custom categories for test@test.com user."""

import asyncio
import sys
from pathlib import Path
import uuid

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.transaction import Category
# Import all models to avoid relationship errors
from app.models import account, holding, transaction, budget, savings_goal, recurring_transaction, notification


async def seed_categories():
    """Seed custom categories for test@test.com user."""
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
        print(f"   Organization ID: {user.organization_id}")

        # Check if categories already exist
        existing = await db.execute(
            select(Category).where(
                Category.organization_id == user.organization_id
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            print("⚠️  Categories already exist. Skipping seed.")
            return

        # Create common custom categories
        categories_data = [
            {"name": "Groceries", "color": "#4CAF50", "plaid": "Food and Drink"},
            {"name": "Restaurants", "color": "#FF9800", "plaid": "Food and Drink"},
            {"name": "Transportation", "color": "#2196F3", "plaid": "Travel"},
            {"name": "Utilities", "color": "#9C27B0", "plaid": "Bills and Utilities"},
            {"name": "Rent/Mortgage", "color": "#F44336", "plaid": "Bills and Utilities"},
            {"name": "Entertainment", "color": "#E91E63", "plaid": "Entertainment"},
            {"name": "Shopping", "color": "#00BCD4", "plaid": "Shops"},
            {"name": "Healthcare", "color": "#009688", "plaid": "Healthcare"},
            {"name": "Fitness", "color": "#8BC34A", "plaid": "Recreation"},
            {"name": "Income", "color": "#4CAF50", "plaid": "Income"},
            {"name": "Subscriptions", "color": "#673AB7", "plaid": "Service"},
        ]

        categories = []
        for cat_data in categories_data:
            category = Category(
                id=uuid.uuid4(),
                organization_id=user.organization_id,
                name=cat_data["name"],
                color=cat_data["color"],
                plaid_category_name=cat_data["plaid"],
            )
            categories.append(category)
            db.add(category)

        await db.commit()

        print(f"\n✅ Created {len(categories)} custom categories:")
        for cat in categories:
            print(f"   - {cat.name} (linked to Plaid: {cat.plaid_category_name})")

        print("\n✨ Categories seeded successfully! You can now create budgets.")


if __name__ == "__main__":
    asyncio.run(seed_categories())
