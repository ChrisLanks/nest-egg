"""Seed database with mock Plaid data for testing."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
from decimal import Decimal
import uuid
import hashlib

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.account import Account, PlaidItem, AccountType, AccountSource
from app.models.transaction import Transaction


async def generate_deduplication_hash(account_id: uuid.UUID, date: date, amount: Decimal, merchant: str) -> str:
    """Generate deduplication hash for transaction."""
    hash_input = f"{account_id}|{date.isoformat()}|{abs(amount):.2f}|{merchant.lower().strip()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


async def seed_mock_data():
    """Seed mock data for test@test.com user."""
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
        print(f"   User ID: {user.id}")

        # Create mock Plaid item
        plaid_item = PlaidItem(
            id=uuid.uuid4(),
            organization_id=user.organization_id,
            user_id=user.id,
            item_id="mock_plaid_item_chase",
            access_token="mock_access_token_encrypted",
            institution_id="ins_3",
            institution_name="Chase",
            is_active=True,
            needs_reauth=False,
            last_synced_at=datetime.utcnow(),
        )
        db.add(plaid_item)
        await db.flush()
        print(f"\n✅ Created mock Plaid item: Chase")

        # Create mock checking account
        checking_account = Account(
            id=uuid.uuid4(),
            organization_id=user.organization_id,
            user_id=user.id,
            plaid_item_id=plaid_item.id,
            name="Chase Checking",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.PLAID,
            external_account_id="mock_chase_checking_1234",
            mask="1234",
            institution_name="Chase",
            current_balance=Decimal("5432.50"),
            available_balance=Decimal("5432.50"),
            balance_as_of=datetime.utcnow(),
            is_active=True,
            is_manual=False,
        )
        db.add(checking_account)
        await db.flush()
        print(f"✅ Created account: {checking_account.name} (****{checking_account.mask})")

        # Create mock credit card account
        credit_card = Account(
            id=uuid.uuid4(),
            organization_id=user.organization_id,
            user_id=user.id,
            plaid_item_id=plaid_item.id,
            name="Chase Sapphire Reserve",
            account_type=AccountType.CREDIT_CARD,
            account_source=AccountSource.PLAID,
            external_account_id="mock_chase_cc_5678",
            mask="5678",
            institution_name="Chase",
            current_balance=Decimal("-1245.67"),  # Negative = you owe this
            available_balance=Decimal("8754.33"),
            limit=Decimal("10000.00"),
            balance_as_of=datetime.utcnow(),
            is_active=True,
            is_manual=False,
        )
        db.add(credit_card)
        await db.flush()
        print(f"✅ Created account: {credit_card.name} (****{credit_card.mask})")

        # Generate mock transactions for the last 60 days
        print(f"\n📊 Generating mock transactions...")
        transactions_data = []
        today = date.today()

        # Checking account transactions
        checking_txns = [
            # Recent transactions (last week)
            {"days_ago": 1, "amount": -45.32, "merchant": "Whole Foods Market", "category": "Food and Drink", "pending": False},
            {"days_ago": 2, "amount": -12.50, "merchant": "Starbucks", "category": "Food and Drink", "pending": False},
            {"days_ago": 3, "amount": -89.99, "merchant": "Shell Gas Station", "category": "Travel", "pending": False},
            {"days_ago": 4, "amount": -156.78, "merchant": "Target", "category": "Shops", "pending": False},
            {"days_ago": 5, "amount": 3500.00, "merchant": "Direct Deposit Salary", "category": "Income", "pending": False},
            {"days_ago": 6, "amount": -67.43, "merchant": "Amazon.com", "category": "Shops", "pending": False},
            {"days_ago": 7, "amount": -125.00, "merchant": "Electric Company", "category": "Bills and Utilities", "pending": False},

            # Last month
            {"days_ago": 15, "amount": -1250.00, "merchant": "Rent Payment", "category": "Bills and Utilities", "pending": False},
            {"days_ago": 18, "amount": -78.90, "merchant": "Verizon Wireless", "category": "Bills and Utilities", "pending": False},
            {"days_ago": 20, "amount": -234.56, "merchant": "Costco", "category": "Shops", "pending": False},
            {"days_ago": 22, "amount": -45.00, "merchant": "Planet Fitness", "category": "Recreation", "pending": False},
            {"days_ago": 25, "amount": -189.99, "merchant": "Best Buy", "category": "Shops", "pending": False},
            {"days_ago": 28, "amount": -67.50, "merchant": "Chipotle", "category": "Food and Drink", "pending": False},
            {"days_ago": 30, "amount": 3500.00, "merchant": "Direct Deposit Salary", "category": "Income", "pending": False},

            # 2 months ago
            {"days_ago": 35, "amount": -1250.00, "merchant": "Rent Payment", "category": "Bills and Utilities", "pending": False},
            {"days_ago": 38, "amount": -156.78, "merchant": "Safeway", "category": "Food and Drink", "pending": False},
            {"days_ago": 42, "amount": -89.00, "merchant": "Netflix", "category": "Entertainment", "pending": False},
            {"days_ago": 45, "amount": 3500.00, "merchant": "Direct Deposit Salary", "category": "Income", "pending": False},
            {"days_ago": 50, "amount": -523.45, "merchant": "Car Insurance", "category": "Bills and Utilities", "pending": False},
            {"days_ago": 55, "amount": -234.90, "merchant": "Whole Foods Market", "category": "Food and Drink", "pending": False},
        ]

        for txn_data in checking_txns:
            txn_date = today - timedelta(days=txn_data["days_ago"])
            dedup_hash = await generate_deduplication_hash(
                checking_account.id,
                txn_date,
                Decimal(str(txn_data["amount"])),
                txn_data["merchant"]
            )

            transaction = Transaction(
                id=uuid.uuid4(),
                organization_id=user.organization_id,
                account_id=checking_account.id,
                external_transaction_id=f"mock_txn_{uuid.uuid4().hex[:12]}",
                date=txn_date,
                amount=Decimal(str(txn_data["amount"])),
                merchant_name=txn_data["merchant"],
                description=f"{txn_data['merchant']} - {txn_data['category']}",
                category_primary=txn_data["category"],
                is_pending=txn_data["pending"],
                deduplication_hash=dedup_hash,
            )
            transactions_data.append(transaction)

        # Credit card transactions
        cc_txns = [
            {"days_ago": 1, "amount": -87.65, "merchant": "Amazon Prime", "category": "Service", "pending": True},
            {"days_ago": 2, "amount": -234.50, "merchant": "Delta Airlines", "category": "Travel", "pending": False},
            {"days_ago": 3, "amount": -45.00, "merchant": "Uber", "category": "Travel", "pending": False},
            {"days_ago": 5, "amount": -156.78, "merchant": "Hotel.com", "category": "Travel", "pending": False},
            {"days_ago": 8, "amount": -89.99, "merchant": "Apple Store", "category": "Shops", "pending": False},
            {"days_ago": 12, "amount": -67.43, "merchant": "Spotify Premium", "category": "Entertainment", "pending": False},
            {"days_ago": 15, "amount": -234.90, "merchant": "Restaurant", "category": "Food and Drink", "pending": False},
            {"days_ago": 20, "amount": -456.78, "merchant": "Home Depot", "category": "Shops", "pending": False},
            {"days_ago": 25, "amount": -123.45, "merchant": "CVS Pharmacy", "category": "Healthcare", "pending": False},
            {"days_ago": 30, "amount": -89.00, "merchant": "Gas Station", "category": "Travel", "pending": False},
        ]

        for txn_data in cc_txns:
            txn_date = today - timedelta(days=txn_data["days_ago"])
            dedup_hash = await generate_deduplication_hash(
                credit_card.id,
                txn_date,
                Decimal(str(txn_data["amount"])),
                txn_data["merchant"]
            )

            transaction = Transaction(
                id=uuid.uuid4(),
                organization_id=user.organization_id,
                account_id=credit_card.id,
                external_transaction_id=f"mock_txn_{uuid.uuid4().hex[:12]}",
                date=txn_date,
                amount=Decimal(str(txn_data["amount"])),
                merchant_name=txn_data["merchant"],
                description=f"{txn_data['merchant']} - {txn_data['category']}",
                category_primary=txn_data["category"],
                is_pending=txn_data["pending"],
                deduplication_hash=dedup_hash,
            )
            transactions_data.append(transaction)

        # Add all transactions
        db.add_all(transactions_data)
        await db.commit()

        print(f"✅ Created {len(checking_txns)} transactions for {checking_account.name}")
        print(f"✅ Created {len(cc_txns)} transactions for {credit_card.name}")
        print(f"\n🎉 Total: {len(transactions_data)} mock transactions created!")
        print(f"\n💡 You can now view these transactions in the app!")


if __name__ == "__main__":
    print("🌱 Seeding mock Plaid data...\n")
    asyncio.run(seed_mock_data())
