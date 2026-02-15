"""Add shared accounts (Quicksilver card and property) for test users."""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.account import Account, AccountType, AccountSource
from app.services.deduplication_service import DeduplicationService

dedup_service = DeduplicationService()


async def add_shared_accounts():
    """Add Quicksilver card and property to both test users."""
    async with AsyncSessionLocal() as db:
        # Get both users
        result = await db.execute(
            select(User).where(User.email.in_(["test@test.com", "test2@test.com"]))
        )
        users = {user.email: user for user in result.scalars().all()}

        if "test@test.com" not in users:
            print("❌ test@test.com not found")
            return

        if "test2@test.com" not in users:
            print("❌ test2@test.com not found")
            return

        user1 = users["test@test.com"]
        user2 = users["test2@test.com"]

        print(f"✓ Found test@test.com (ID: {user1.id})")
        print(f"✓ Found test2@test.com (ID: {user2.id})")

        # 1. Add Quicksilver Card to both users
        print("\n1. Adding Capital One Quicksilver cards...")

        quicksilver_hash = dedup_service.calculate_manual_account_hash(
            account_type=AccountType.CREDIT_CARD,
            institution_name="Capital One",
            mask="1987",
            name="Quicksilver Card"
        )

        # User 1's Quicksilver
        quicksilver1 = Account(
            id=uuid4(),
            organization_id=user1.organization_id,
            user_id=user1.id,
            name="Quicksilver Card",
            account_type=AccountType.CREDIT_CARD,
            account_source=AccountSource.MANUAL,
            institution_name="Capital One",
            mask="1987",
            current_balance=Decimal("-450.25"),
            plaid_item_hash=quicksilver_hash,
            is_manual=True,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(quicksilver1)

        # User 2's Quicksilver (same hash!)
        quicksilver2 = Account(
            id=uuid4(),
            organization_id=user2.organization_id,
            user_id=user2.id,
            name="Quicksilver Card",
            account_type=AccountType.CREDIT_CARD,
            account_source=AccountSource.MANUAL,
            institution_name="Capital One",
            mask="1987",
            current_balance=Decimal("-450.25"),
            plaid_item_hash=quicksilver_hash,
            is_manual=True,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(quicksilver2)

        print(f"   ✓ Added Quicksilver for test@test.com")
        print(f"   ✓ Added Quicksilver for test2@test.com")
        print(f"   Hash: {quicksilver_hash[:16]}...")

        # 2. Add Property to both users
        print("\n2. Adding shared property...")

        property_hash = dedup_service.calculate_manual_account_hash(
            account_type=AccountType.PROPERTY,
            institution_name="Zillow Estimate",
            mask=None,
            name="456 Oak Avenue"
        )

        # User 1's Property
        property1 = Account(
            id=uuid4(),
            organization_id=user1.organization_id,
            user_id=user1.id,
            name="456 Oak Avenue",
            account_type=AccountType.PROPERTY,
            account_source=AccountSource.MANUAL,
            institution_name="Zillow Estimate",
            mask=None,
            current_balance=Decimal("450000.00"),
            plaid_item_hash=property_hash,
            is_manual=True,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(property1)

        # User 2's Property (same hash!)
        property2 = Account(
            id=uuid4(),
            organization_id=user2.organization_id,
            user_id=user2.id,
            name="456 Oak Avenue",
            account_type=AccountType.PROPERTY,
            account_source=AccountSource.MANUAL,
            institution_name="Zillow Estimate",
            mask=None,
            current_balance=Decimal("450000.00"),
            plaid_item_hash=property_hash,
            is_manual=True,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(property2)

        print(f"   ✓ Added Property for test@test.com")
        print(f"   ✓ Added Property for test2@test.com")
        print(f"   Hash: {property_hash[:16]}...")

        await db.commit()

        print("\n" + "="*60)
        print("✅ SUCCESS! Shared accounts created")
        print("="*60)
        print("\nThese accounts will appear as MULTI in combined view:")
        print("  • Quicksilver Card (Capital One ••1987)")
        print("  • 456 Oak Avenue (Property)")
        print("\nRefresh your browser to see the changes!")


if __name__ == "__main__":
    asyncio.run(add_shared_accounts())
