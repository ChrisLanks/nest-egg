"""Development/testing endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date
from decimal import Decimal
import uuid
import hashlib

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.account import Account, PlaidItem, AccountType, AccountSource
from app.models.transaction import Transaction

router = APIRouter()


async def generate_deduplication_hash(account_id: uuid.UUID, date_val: date, amount: Decimal, merchant: str) -> str:
    """Generate deduplication hash for transaction."""
    hash_input = f"{account_id}|{date_val.isoformat()}|{abs(amount):.2f}|{merchant.lower().strip()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


@router.get("/debug-transactions")
async def debug_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint to see transactions and accounts."""
    from sqlalchemy import select, func

    # Get transaction count
    txn_count = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.organization_id == current_user.organization_id
        )
    )

    # Get account count
    acc_count = await db.execute(
        select(func.count(Account.id)).where(
            Account.organization_id == current_user.organization_id
        )
    )

    # Get sample transactions
    txns = await db.execute(
        select(Transaction)
        .where(Transaction.organization_id == current_user.organization_id)
        .order_by(Transaction.date.desc())
        .limit(5)
    )
    sample_txns = txns.scalars().all()

    return {
        "user_email": current_user.email,
        "organization_id": str(current_user.organization_id),
        "transaction_count": txn_count.scalar(),
        "account_count": acc_count.scalar(),
        "sample_transactions": [
            {
                "id": str(t.id),
                "date": str(t.date),
                "merchant": t.merchant_name,
                "amount": float(t.amount),
                "account_id": str(t.account_id),
            }
            for t in sample_txns
        ],
    }


async def seed_mock_data_internal(db: AsyncSession, user: User) -> dict:
    """Internal function to seed mock data for a user."""
    # Create mock checking account
    checking_account = Account(
        id=uuid.uuid4(),
        organization_id=user.organization_id,
        user_id=user.id,
        name="Chase Checking",
        account_type=AccountType.CHECKING,
        account_source=AccountSource.PLAID,
        institution_name="Chase",
        mask="1234",
        current_balance=Decimal("5432.50"),
    )
    db.add(checking_account)
    await db.flush()

    # Create mock credit card account
    credit_account = Account(
        id=uuid.uuid4(),
        organization_id=user.organization_id,
        user_id=user.id,
        name="Chase Sapphire",
        account_type=AccountType.CREDIT_CARD,
        account_source=AccountSource.PLAID,
        institution_name="Chase",
        mask="5678",
        current_balance=Decimal("-1245.67"),
    )
    db.add(credit_account)
    await db.flush()

    # Mock transactions
    checking_txns = [
        {"days_ago": 1, "amount": -45.32, "merchant": "Whole Foods Market", "category": "Food and Drink"},
        {"days_ago": 2, "amount": -12.50, "merchant": "Starbucks", "category": "Food and Drink"},
        {"days_ago": 3, "amount": -89.99, "merchant": "Shell Gas Station", "category": "Travel"},
        {"days_ago": 4, "amount": -156.78, "merchant": "Target", "category": "Shops"},
        {"days_ago": 5, "amount": 3500.00, "merchant": "Direct Deposit Salary", "category": "Income"},
        {"days_ago": 6, "amount": -67.43, "merchant": "Amazon.com", "category": "Shops"},
        {"days_ago": 7, "amount": -125.00, "merchant": "Electric Company", "category": "Bills and Utilities"},
        {"days_ago": 10, "amount": -45.00, "merchant": "Netflix", "category": "Recreation"},
        {"days_ago": 12, "amount": -89.99, "merchant": "Spotify", "category": "Recreation"},
        {"days_ago": 15, "amount": -1250.00, "merchant": "Rent Payment", "category": "Bills and Utilities"},
        {"days_ago": 18, "amount": -78.90, "merchant": "Verizon Wireless", "category": "Bills and Utilities"},
        {"days_ago": 20, "amount": -234.56, "merchant": "Costco", "category": "Shops"},
        {"days_ago": 22, "amount": -45.00, "merchant": "Planet Fitness", "category": "Recreation"},
        {"days_ago": 25, "amount": -189.99, "merchant": "Best Buy", "category": "Shops"},
        {"days_ago": 28, "amount": -67.50, "merchant": "Chipotle", "category": "Food and Drink"},
        {"days_ago": 30, "amount": 3500.00, "merchant": "Direct Deposit Salary", "category": "Income"},
        {"days_ago": 35, "amount": -1250.00, "merchant": "Rent Payment", "category": "Bills and Utilities"},
        {"days_ago": 38, "amount": -156.78, "merchant": "Safeway", "category": "Food and Drink"},
        {"days_ago": 40, "amount": -89.50, "merchant": "Uber", "category": "Travel"},
        {"days_ago": 42, "amount": -234.90, "merchant": "Home Depot", "category": "Shops"},
        {"days_ago": 45, "amount": -67.80, "merchant": "CVS Pharmacy", "category": "Health"},
        {"days_ago": 48, "amount": -125.00, "merchant": "Comcast", "category": "Bills and Utilities"},
        {"days_ago": 50, "amount": -45.67, "merchant": "Panera Bread", "category": "Food and Drink"},
        {"days_ago": 52, "amount": -234.00, "merchant": "Apple Store", "category": "Shops"},
        {"days_ago": 55, "amount": -78.90, "merchant": "AT&T", "category": "Bills and Utilities"},
    ]

    created_count = 0
    for txn_data in checking_txns:
        txn_date = date.today() - timedelta(days=txn_data["days_ago"])
        amount = Decimal(str(txn_data["amount"]))

        dedup_hash = await generate_deduplication_hash(
            checking_account.id, txn_date, amount, txn_data["merchant"]
        )

        transaction = Transaction(
            id=uuid.uuid4(),
            organization_id=user.organization_id,
            account_id=checking_account.id,
            date=txn_date,
            amount=amount,
            merchant_name=txn_data["merchant"],
            category_primary=txn_data.get("category"),
            is_pending=False,
            deduplication_hash=dedup_hash,
        )
        db.add(transaction)
        created_count += 1

    return {
        "transactions_created": created_count,
        "accounts_created": 2,
    }


@router.post("/seed-mock-data")
async def seed_mock_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seed mock transaction data for the current user."""
    result = await seed_mock_data_internal(db, current_user)
    await db.commit()

    return {
        "message": "Mock data seeded successfully",
        **result,
    }
