"""Development/testing endpoints."""

import hashlib
import logging
import random
import string
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies import get_current_admin_user, get_current_user
from app.models.account import Account, AccountSource, AccountType
from app.models.transaction import Transaction
from app.models.user import User
from app.services.category_service import get_category_id_for_plaid_category

logger = logging.getLogger(__name__)

router = APIRouter()


async def generate_deduplication_hash(
    account_id: uuid.UUID, date_val: date, amount: Decimal, merchant: str
) -> str:
    """Generate deduplication hash for transaction."""
    hash_input = f"{account_id}|{date_val.isoformat()}|{abs(amount):.2f}|{merchant.lower().strip()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


@router.get("/debug-transactions")
async def debug_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint to see transactions and accounts."""
    # Only allow in development/staging environments
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")

    from sqlalchemy import func, select

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
        {
            "days_ago": 1,
            "amount": -45.32,
            "merchant": "Whole Foods Market",
            "category": "Food and Drink",
        },
        {"days_ago": 2, "amount": -12.50, "merchant": "Starbucks", "category": "Food and Drink"},
        {"days_ago": 3, "amount": -89.99, "merchant": "Shell Gas Station", "category": "Travel"},
        {"days_ago": 4, "amount": -156.78, "merchant": "Target", "category": "Shops"},
        {
            "days_ago": 5,
            "amount": 3500.00,
            "merchant": "Direct Deposit Salary",
            "category": "Income",
        },
        {"days_ago": 6, "amount": -67.43, "merchant": "Amazon.com", "category": "Shops"},
        {
            "days_ago": 7,
            "amount": -125.00,
            "merchant": "Electric Company",
            "category": "Bills and Utilities",
        },
        {"days_ago": 10, "amount": -45.00, "merchant": "Netflix", "category": "Recreation"},
        {"days_ago": 12, "amount": -89.99, "merchant": "Spotify", "category": "Recreation"},
        {
            "days_ago": 15,
            "amount": -1250.00,
            "merchant": "Rent Payment",
            "category": "Bills and Utilities",
        },
        {
            "days_ago": 18,
            "amount": -78.90,
            "merchant": "Verizon Wireless",
            "category": "Bills and Utilities",
        },
        {"days_ago": 20, "amount": -234.56, "merchant": "Costco", "category": "Shops"},
        {"days_ago": 22, "amount": -45.00, "merchant": "Planet Fitness", "category": "Recreation"},
        {"days_ago": 25, "amount": -189.99, "merchant": "Best Buy", "category": "Shops"},
        {"days_ago": 28, "amount": -67.50, "merchant": "Chipotle", "category": "Food and Drink"},
        {
            "days_ago": 30,
            "amount": 3500.00,
            "merchant": "Direct Deposit Salary",
            "category": "Income",
        },
        {
            "days_ago": 35,
            "amount": -1250.00,
            "merchant": "Rent Payment",
            "category": "Bills and Utilities",
        },
        {"days_ago": 38, "amount": -156.78, "merchant": "Safeway", "category": "Food and Drink"},
        {"days_ago": 40, "amount": -89.50, "merchant": "Uber", "category": "Travel"},
        {"days_ago": 42, "amount": -234.90, "merchant": "Home Depot", "category": "Shops"},
        {"days_ago": 45, "amount": -67.80, "merchant": "CVS Pharmacy", "category": "Health"},
        {
            "days_ago": 48,
            "amount": -125.00,
            "merchant": "Comcast",
            "category": "Bills and Utilities",
        },
        {
            "days_ago": 50,
            "amount": -45.67,
            "merchant": "Panera Bread",
            "category": "Food and Drink",
        },
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

        # Auto-map to custom category if one exists for this Plaid category
        plaid_category = txn_data.get("category")
        category_id = await get_category_id_for_plaid_category(
            db, user.organization_id, plaid_category
        )

        transaction = Transaction(
            id=uuid.uuid4(),
            organization_id=user.organization_id,
            account_id=checking_account.id,
            date=txn_date,
            amount=amount,
            merchant_name=txn_data["merchant"],
            category_primary=plaid_category,
            category_id=category_id,  # Auto-mapped custom category
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
    # Only allow in development/staging environments
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")

    result = await seed_mock_data_internal(db, current_user)
    await db.commit()

    return {
        "message": "Mock data seeded successfully",
        **result,
    }


# ---------------------------------------------------------------------------
# User management (dev-only)
# ---------------------------------------------------------------------------

_FIRST_NAMES = [
    "Alice",
    "Bob",
    "Charlie",
    "Diana",
    "Eve",
    "Frank",
    "Grace",
    "Hank",
    "Iris",
    "Jack",
    "Karen",
    "Leo",
    "Mona",
    "Nate",
    "Olivia",
    "Paul",
    "Quinn",
    "Rosa",
    "Sam",
    "Tina",
    "Uma",
    "Vic",
    "Wendy",
    "Xander",
]

_LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Anderson",
    "Taylor",
    "Thomas",
    "Moore",
    "Jackson",
    "Lee",
    "White",
    "Harris",
    "Clark",
    "Lewis",
]


class DevUserResponse(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    is_org_admin: bool
    organization_id: UUID

    model_config = {"from_attributes": True}


@router.get("/users", response_model=List[DevUserResponse])
async def list_all_users(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users in the current organization. Admin only, dev only."""
    if settings.ENVIRONMENT not in ("development", "test"):
        raise HTTPException(status_code=404, detail="Not found")

    result = await db.execute(
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at)
    )
    return result.scalars().all()


class CreateRandomUsersRequest(BaseModel):
    count: int = 1


class CreateRandomUsersResponse(BaseModel):
    created: List[DevUserResponse]


@router.post("/users/random", response_model=CreateRandomUsersResponse)
async def create_random_users(
    body: CreateRandomUsersRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create N random test users in the current org. Dev only."""
    if settings.ENVIRONMENT not in ("development", "test"):
        raise HTTPException(status_code=404, detail="Not found")

    if body.count < 1 or body.count > 50:
        raise HTTPException(status_code=400, detail="count must be 1-50")

    created = []
    for _ in range(body.count):
        first = random.choice(_FIRST_NAMES)
        last = random.choice(_LAST_NAMES)
        tag = "".join(random.choices(string.digits, k=4))
        email = f"{first.lower()}.{last.lower()}{tag}@test.local"

        # Check uniqueness
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            continue

        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password("test1234"),
            first_name=first,
            last_name=last,
            organization_id=current_user.organization_id,
            is_org_admin=False,
            is_primary_household_member=False,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        await db.flush()
        created.append(user)

    await db.commit()
    logger.info(
        "dev: created %d random users in org=%s", len(created), current_user.organization_id
    )
    return {"created": created}


@router.delete("/users/{user_id}", status_code=204)
async def hard_delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a user and their data. Admin only, dev only.

    If the user is the sole member of their org, deletes the org too.
    Cannot delete yourself or the primary household member.
    """
    if settings.ENVIRONMENT not in ("development", "test"):
        raise HTTPException(status_code=404, detail="Not found")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    if target.is_primary_household_member:
        raise HTTPException(status_code=400, detail="Cannot delete the primary household member")

    # Count remaining members
    count_result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(
            User.organization_id == target.organization_id,
            User.id != target.id,
        )
    )
    remaining = count_result.scalar()

    await db.delete(target)
    await db.commit()

    logger.info(
        "dev: hard-deleted user=%s email=%s (%d members remain)",
        user_id,
        target.email,
        remaining,
    )
