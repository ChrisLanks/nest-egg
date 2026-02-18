"""Seed test data for multi-user household testing.

Creates test2@test.com user with dummy data including:
- Separate accounts with transactions
- Overlapping accounts (same as test@test.com)
- Ready to be invited to test@test.com's household
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User, Organization
from app.models.account import Account
from app.models.transaction import Transaction
from app.services.deduplication_service import DeduplicationService

dedup_service = DeduplicationService()


async def create_test_user_2(db: AsyncSession):
    """Create test2@test.com user with own organization."""
    print("\n1. Creating test2@test.com user...")

    # Check if user already exists
    result = await db.execute(select(User).where(User.email == "test2@test.com"))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        print(f"   ✓ User already exists (ID: {existing_user.id})")
        return existing_user

    # Create organization for test2
    org = Organization(
        id=uuid4(),
        name="Test2 Household",
        created_at=datetime.utcnow(),
    )
    db.add(org)
    await db.flush()

    # Create user
    user = User(
        id=uuid4(),
        email="test2@test.com",
        password_hash=hash_password("test1234"),
        first_name="Test2",
        last_name="User",
        organization_id=org.id,
        is_org_admin=True,
        is_primary_household_member=True,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()

    print(f"   ✓ Created user: test2@test.com")
    print(f"   ✓ Organization ID: {org.id}")
    print(f"   ✓ User ID: {user.id}")

    return user


async def create_unique_accounts(db: AsyncSession, user: User):
    """Create unique accounts for test2 (not shared with test@test.com)."""
    print("\n2. Creating unique accounts for test2@test.com...")

    accounts = [
        {
            "name": "Wells Fargo Checking",
            "account_type": "depository",
            "subtype": "checking",
            "current_balance": Decimal("3500.00"),
            "mask": "8765",
            "institution_name": "Wells Fargo",
        },
        {
            "name": "Ally Savings",
            "account_type": "depository",
            "subtype": "savings",
            "current_balance": Decimal("15000.00"),
            "mask": "4321",
            "institution_name": "Ally Bank",
        },
        {
            "name": "Capital One Visa",
            "account_type": "credit",
            "subtype": "credit card",
            "current_balance": Decimal("-850.00"),
            "mask": "9999",
            "institution_name": "Capital One",
        },
    ]

    created_accounts = []
    for acc_data in accounts:
        account = Account(
            id=uuid4(),
            organization_id=user.organization_id,
            user_id=user.id,
            name=acc_data["name"],
            account_type=acc_data["account_type"],
            subtype=acc_data["subtype"],
            current_balance=acc_data["current_balance"],
            available_balance=acc_data["current_balance"],
            mask=acc_data["mask"],
            institution_name=acc_data["institution_name"],
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(account)
        created_accounts.append(account)
        print(f"   ✓ Created: {acc_data['name']} (${acc_data['current_balance']})")

    await db.commit()
    return created_accounts


async def get_test_user_1_accounts(db: AsyncSession):
    """Get test@test.com user's accounts to create overlaps."""
    print("\n3. Finding test@test.com's accounts for overlap...")

    # Get test@test.com user
    result = await db.execute(select(User).where(User.email == "test@test.com"))
    test_user_1 = result.scalar_one_or_none()

    if not test_user_1:
        print("   ⚠️  test@test.com not found - skipping overlap accounts")
        return None, []

    # Get their accounts
    result = await db.execute(
        select(Account).where(Account.user_id == test_user_1.id, Account.is_active.is_(True))
    )
    accounts = result.scalars().all()

    print(f"   ✓ Found {len(accounts)} accounts for test@test.com")
    for acc in accounts:
        print(f"     - {acc.name} (Mask: {acc.mask})")

    return test_user_1, accounts


async def create_overlapping_accounts(db: AsyncSession, user2: User, user1_accounts: list):
    """Create overlapping accounts for test2 (same Plaid item as test1)."""
    print("\n4. Creating overlapping accounts (shared with test@test.com)...")

    if not user1_accounts:
        print("   ⚠️  No accounts to overlap")
        return []

    overlapping_accounts = []

    # Take first 2 accounts from test@test.com as overlaps
    for acc in user1_accounts[:2]:
        # Create matching account for test2
        overlap_account = Account(
            id=uuid4(),
            organization_id=user2.organization_id,
            user_id=user2.id,
            name=acc.name,  # Same name
            account_type=acc.account_type,
            subtype=acc.subtype,
            current_balance=acc.current_balance,  # Same balance
            available_balance=acc.available_balance,
            mask=acc.mask,  # Same mask
            institution_name=acc.institution_name,
            external_account_id=acc.external_account_id,  # KEY: Same external ID
            plaid_item_id=acc.plaid_item_id,  # KEY: Same plaid item
            is_active=True,
            created_at=datetime.utcnow(),
        )

        # Calculate and set plaid_item_hash for duplicate detection
        if acc.plaid_item_id and acc.external_account_id:
            overlap_account.plaid_item_hash = dedup_service.calculate_account_hash(
                acc.plaid_item_id, acc.external_account_id
            )

        db.add(overlap_account)
        overlapping_accounts.append(overlap_account)

        print(f"   ✓ Created overlap: {acc.name}")
        print(
            f"     Hash: {overlap_account.plaid_item_hash[:16] if overlap_account.plaid_item_hash else 'None'}..."
        )

    await db.commit()
    return overlapping_accounts


async def create_transactions(db: AsyncSession, accounts: list):
    """Create sample transactions for test2's accounts."""
    print("\n5. Creating sample transactions...")

    transaction_count = 0
    base_date = datetime.utcnow().date()

    for account in accounts:
        # Skip credit cards for simplicity
        if account.account_type == "credit":
            continue

        # Create 10 transactions per account
        transactions = [
            {
                "date": base_date - timedelta(days=25),
                "amount": Decimal("-125.50"),
                "merchant_name": "Whole Foods",
                "description": "Grocery shopping",
                "category_primary": "Food and Drink",
            },
            {
                "date": base_date - timedelta(days=23),
                "amount": Decimal("-45.00"),
                "merchant_name": "Shell Gas",
                "description": "Gas station",
                "category_primary": "Transportation",
            },
            {
                "date": base_date - timedelta(days=20),
                "amount": Decimal("2500.00"),
                "merchant_name": "ACME Corp",
                "description": "Paycheck deposit",
                "category_primary": "Income",
            },
            {
                "date": base_date - timedelta(days=18),
                "amount": Decimal("-1200.00"),
                "merchant_name": "Property Management",
                "description": "Rent payment",
                "category_primary": "Home",
            },
            {
                "date": base_date - timedelta(days=15),
                "amount": Decimal("-89.99"),
                "merchant_name": "Amazon",
                "description": "Online shopping",
                "category_primary": "Shopping",
            },
            {
                "date": base_date - timedelta(days=12),
                "amount": Decimal("-65.00"),
                "merchant_name": "AT&T",
                "description": "Phone bill",
                "category_primary": "Bills",
            },
            {
                "date": base_date - timedelta(days=10),
                "amount": Decimal("-150.00"),
                "merchant_name": "Target",
                "description": "Household items",
                "category_primary": "Shopping",
            },
            {
                "date": base_date - timedelta(days=7),
                "amount": Decimal("-55.00"),
                "merchant_name": "LA Fitness",
                "description": "Gym membership",
                "category_primary": "Recreation",
            },
            {
                "date": base_date - timedelta(days=5),
                "amount": Decimal("2500.00"),
                "merchant_name": "ACME Corp",
                "description": "Paycheck deposit",
                "category_primary": "Income",
            },
            {
                "date": base_date - timedelta(days=2),
                "amount": Decimal("-42.50"),
                "merchant_name": "Starbucks",
                "description": "Coffee",
                "category_primary": "Food and Drink",
            },
        ]

        for txn_data in transactions:
            transaction = Transaction(
                id=uuid4(),
                organization_id=account.organization_id,
                account_id=account.id,
                external_transaction_id=f"test2-{uuid4()}",
                date=txn_data["date"],
                amount=txn_data["amount"],
                merchant_name=txn_data["merchant_name"],
                description=txn_data["description"],
                category_primary=txn_data["category_primary"],
                is_pending=False,
                created_at=datetime.utcnow(),
            )
            db.add(transaction)
            transaction_count += 1

        print(f"   ✓ Added 10 transactions for {account.name}")

    await db.commit()
    print(f"   ✓ Total: {transaction_count} transactions created")


async def print_summary(db: AsyncSession):
    """Print summary of created data."""
    print("\n" + "=" * 60)
    print("SEED DATA SUMMARY")
    print("=" * 60)

    # Get test2 user
    result = await db.execute(select(User).where(User.email == "test2@test.com"))
    user2 = result.scalar_one()

    # Count accounts
    result = await db.execute(
        select(Account).where(Account.user_id == user2.id, Account.is_active.is_(True))
    )
    accounts = result.scalars().all()

    # Count transactions
    result = await db.execute(
        select(Transaction).where(Transaction.organization_id == user2.organization_id)
    )
    transactions = result.scalars().all()

    print(f"\n✅ Created test2@test.com:")
    print(f"   Email: test2@test.com")
    print(f"   Password: test1234")
    print(f"   Organization: {user2.organization_id}")
    print(f"   Accounts: {len(accounts)}")
    print(f"   Transactions: {len(transactions)}")

    print(f"\n📊 Account Summary:")
    for acc in accounts:
        has_hash = "✓" if acc.plaid_item_hash else "✗"
        overlap = " [OVERLAP]" if acc.plaid_item_hash else ""
        print(f"   {has_hash} {acc.name}: ${acc.current_balance}{overlap}")

    print(f"\n📝 Next Steps:")
    print(f"   1. Login as test@test.com")
    print(f"   2. Go to Household Settings")
    print(f"   3. Invite test2@test.com")
    print(f"   4. Login as test2@test.com")
    print(f"   5. Accept invitation")
    print(f"   6. Test Combined vs Individual views")
    print(f"   7. Verify overlapping accounts show once in Combined view")


async def main():
    """Run seed script."""
    print("=" * 60)
    print("Multi-User Household Test Data Seeder")
    print("=" * 60)

    async for db in get_db():
        try:
            # Create test2 user
            user2 = await create_test_user_2(db)

            # Create unique accounts for test2
            unique_accounts = await create_unique_accounts(db, user2)

            # Get test@test.com accounts to create overlaps
            user1, user1_accounts = await get_test_user_1_accounts(db)

            # Create overlapping accounts
            await create_overlapping_accounts(db, user2, user1_accounts)

            # Create transactions for unique accounts only (overlaps share transactions)
            await create_transactions(db, unique_accounts)

            # Print summary
            await print_summary(db)

            print("\n" + "=" * 60)
            print("✅ SEED DATA COMPLETE!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            import traceback

            traceback.print_exc()
            raise
        finally:
            await db.close()
        break  # Only use first session


if __name__ == "__main__":
    asyncio.run(main())
