"""Development/testing endpoints."""

import hashlib
import logging
import random
import string
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
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
    # Only allow in development/test environments
    if settings.ENVIRONMENT not in ("development", "test"):
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


@router.post("/seed-mock-data", response_model=Dict[str, Any])
async def seed_mock_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seed mock transaction data for the current user."""
    # Only allow in development/test environments
    if settings.ENVIRONMENT not in ("development", "test"):
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


async def seed_planning_data_internal(db: AsyncSession, user: "User") -> dict:
    """Seed realistic planning data for holdings, tax lots, dividends, pension, match, insurance."""
    from app.models.holding import Holding
    from app.models.dividend import DividendIncome, IncomeType
    from app.models.tax_lot import TaxLot
    from app.models.account import AccountType, AccountSource, TaxTreatment

    today = date.today()
    org_id = user.organization_id
    user_id = user.id

    summary: dict = {
        "accounts_created": 0,
        "holdings_created": 0,
        "tax_lots_created": 0,
        "dividends_created": 0,
    }

    # ------------------------------------------------------------------
    # Helper: get-or-create account by name
    # ------------------------------------------------------------------
    async def get_or_create_account(name: str, account_type: AccountType, **kwargs) -> "Account":
        result = await db.execute(
            select(Account).where(
                Account.organization_id == org_id,
                Account.name == name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        acct = Account(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            name=name,
            account_type=account_type,
            account_source=AccountSource.MANUAL,
            is_manual=True,
            **kwargs,
        )
        db.add(acct)
        await db.flush()
        summary["accounts_created"] += 1
        return acct

    # ------------------------------------------------------------------
    # 1. Brokerage account (taxable)
    # ------------------------------------------------------------------
    brokerage = await get_or_create_account(
        "Vanguard Taxable Brokerage",
        AccountType.BROKERAGE,
        tax_treatment=TaxTreatment.TAXABLE,
        institution_name="Vanguard",
        current_balance=Decimal("185000.00"),
    )

    # ------------------------------------------------------------------
    # 2. Traditional IRA / pre-tax account
    # ------------------------------------------------------------------
    trad_ira = await get_or_create_account(
        "Fidelity Traditional IRA",
        AccountType.RETIREMENT_IRA,
        tax_treatment=TaxTreatment.PRE_TAX,
        institution_name="Fidelity",
        current_balance=Decimal("210000.00"),
    )

    # ------------------------------------------------------------------
    # 3. Roth IRA
    # ------------------------------------------------------------------
    roth_ira = await get_or_create_account(
        "Vanguard Roth IRA",
        AccountType.RETIREMENT_ROTH,
        tax_treatment=TaxTreatment.ROTH,
        institution_name="Vanguard",
        current_balance=Decimal("95000.00"),
    )

    # ------------------------------------------------------------------
    # 4. 401(k) with employer match
    # ------------------------------------------------------------------
    k401 = await get_or_create_account(
        "401(k) - Employer Match",
        AccountType.RETIREMENT_401K,
        tax_treatment=TaxTreatment.PRE_TAX,
        institution_name="Fidelity",
        current_balance=Decimal("320000.00"),
        employer_match_percent=Decimal("50.0"),
        employer_match_limit_percent=Decimal("6.0"),
        annual_salary="120000",
    )

    # ------------------------------------------------------------------
    # 5. Pension account
    # ------------------------------------------------------------------
    pension = await get_or_create_account(
        "Employer Pension Plan",
        AccountType.PENSION,
        institution_name="State Pension Fund",
        current_balance=Decimal("0.00"),
        monthly_benefit=Decimal("2500.00"),
        pension_lump_sum_value=Decimal("450000.00"),
        pension_cola_rate=Decimal("0.020"),
        pension_survivor_pct=Decimal("50.0"),
        pension_years_of_service=Decimal("25.0"),
    )

    # ------------------------------------------------------------------
    # 6. Life Insurance cash value
    # ------------------------------------------------------------------
    insurance = await get_or_create_account(
        "Term Life Insurance",
        AccountType.LIFE_INSURANCE_CASH_VALUE,
        institution_name="Northwestern Mutual",
        current_balance=Decimal("50000.00"),
    )

    # ------------------------------------------------------------------
    # 7. Holdings across accounts
    # ------------------------------------------------------------------
    holding_specs = [
        # (account, ticker, name, shares, price, cost_basis_per_share, asset_class, asset_type, expense_ratio)
        (brokerage, "VTI", "Vanguard Total Stock Market ETF", Decimal("150.0"), Decimal("240.00"), Decimal("185.00"), "domestic", "etf", Decimal("0.0003")),
        (brokerage, "FSKAX", "Fidelity Total Market Index Fund", Decimal("200.0"), Decimal("120.00"), Decimal("95.00"), "domestic", "mutual_fund", Decimal("0.0000")),
        (brokerage, "VNQ", "Vanguard Real Estate ETF", Decimal("80.0"), Decimal("87.00"), Decimal("92.00"), "other", "etf", Decimal("0.0012")),
        (trad_ira, "BND", "Vanguard Total Bond Market ETF", Decimal("300.0"), Decimal("73.00"), Decimal("76.00"), "bond", "etf", Decimal("0.0003")),
        (trad_ira, "VXUS", "Vanguard Total International Stock ETF", Decimal("250.0"), Decimal("58.00"), Decimal("52.00"), "international", "etf", Decimal("0.0007")),
        (roth_ira, "QQQ", "Invesco QQQ Trust", Decimal("60.0"), Decimal("470.00"), Decimal("350.00"), "domestic", "etf", Decimal("0.0020")),
        (roth_ira, "VXUS", "Vanguard Total International Stock ETF", Decimal("100.0"), Decimal("58.00"), Decimal("48.00"), "international", "etf", Decimal("0.0007")),
        (k401, "FSKAX", "Fidelity Total Market Index Fund", Decimal("500.0"), Decimal("120.00"), Decimal("75.00"), "domestic", "mutual_fund", Decimal("0.0000")),
    ]

    created_holdings: list[tuple] = []  # (account, holding) pairs
    for acct, ticker, name, shares, price, cost_basis, asset_class, asset_type, er in holding_specs:
        # Check if holding already exists for this account+ticker
        existing = await db.execute(
            select(Holding).where(
                Holding.account_id == acct.id,
                Holding.ticker == ticker,
            )
        )
        holding = existing.scalar_one_or_none()
        if holding is None:
            holding = Holding(
                id=uuid.uuid4(),
                account_id=acct.id,
                organization_id=org_id,
                ticker=ticker,
                name=name,
                shares=shares,
                cost_basis_per_share=cost_basis,
                total_cost_basis=(cost_basis * shares).quantize(Decimal("0.01")),
                current_price_per_share=price,
                current_total_value=(price * shares).quantize(Decimal("0.01")),
                asset_class=asset_class,
                asset_type=asset_type,
                expense_ratio=er,
            )
            db.add(holding)
            await db.flush()
            summary["holdings_created"] += 1
        created_holdings.append((acct, holding))

    # ------------------------------------------------------------------
    # 8. Tax lots (attach to brokerage VTI holding if it was created)
    # ------------------------------------------------------------------
    # Find the brokerage VTI holding
    vti_holding_result = await db.execute(
        select(Holding).where(
            Holding.account_id == brokerage.id,
            Holding.ticker == "VTI",
        )
    )
    vti_holding = vti_holding_result.scalar_one_or_none()

    if vti_holding:
        lot_specs = [
            # (days_ago, quantity, cost_basis_per_share, is_closed)
            (10,  Decimal("20.0"), Decimal("238.00"), False),   # very short term
            (340, Decimal("30.0"), Decimal("210.00"), False),   # approaching 1-year
            (400, Decimal("25.0"), Decimal("195.00"), False),   # long term
            (730, Decimal("40.0"), Decimal("160.00"), False),   # 2-year long term gain
            (500, Decimal("15.0"), Decimal("260.00"), False),   # long term with a loss
        ]
        for days_ago, qty, cb_per_share, is_closed in lot_specs:
            acq_date = today - timedelta(days=days_ago)
            total_cb = (cb_per_share * qty).quantize(Decimal("0.01"))

            # Check if lot already exists (by account + acquisition_date + quantity)
            existing_lot = await db.execute(
                select(TaxLot).where(
                    TaxLot.holding_id == vti_holding.id,
                    TaxLot.acquisition_date == acq_date,
                )
            )
            if existing_lot.scalar_one_or_none() is None:
                lot = TaxLot(
                    id=uuid.uuid4(),
                    organization_id=org_id,
                    holding_id=vti_holding.id,
                    account_id=brokerage.id,
                    acquisition_date=acq_date,
                    quantity=qty,
                    cost_basis_per_share=cb_per_share,
                    total_cost_basis=total_cb,
                    remaining_quantity=qty,
                    is_closed=is_closed,
                )
                db.add(lot)
                summary["tax_lots_created"] += 1

    await db.flush()

    # ------------------------------------------------------------------
    # 9. Dividend income records — spread across current year
    # ------------------------------------------------------------------
    current_year = today.year
    div_specs = [
        # (ticker, month, amount, income_type)
        ("VTI",   1,  Decimal("185.00"), IncomeType.QUALIFIED_DIVIDEND),
        ("BND",   1,  Decimal("312.00"), IncomeType.INTEREST),
        ("VTI",   2,  Decimal("50.00"),  IncomeType.QUALIFIED_DIVIDEND),
        ("VNQ",   2,  Decimal("210.00"), IncomeType.DIVIDEND),
        ("FSKAX", 3,  Decimal("95.00"),  IncomeType.QUALIFIED_DIVIDEND),
        ("BND",   4,  Decimal("298.00"), IncomeType.INTEREST),
        ("VTI",   4,  Decimal("190.00"), IncomeType.QUALIFIED_DIVIDEND),
        ("VNQ",   5,  Decimal("225.00"), IncomeType.DIVIDEND),
        ("QQQ",   5,  Decimal("75.00"),  IncomeType.QUALIFIED_DIVIDEND),
        ("BND",   6,  Decimal("315.00"), IncomeType.INTEREST),
        ("FSKAX", 6,  Decimal("110.00"), IncomeType.QUALIFIED_DIVIDEND),
        ("VTI",   7,  Decimal("200.00"), IncomeType.QUALIFIED_DIVIDEND),
    ]

    for ticker, month, amount, income_type in div_specs:
        # Only seed months that have already passed or are current
        pay_day = min(15, 28)  # always valid
        pay_date_val = date(current_year, month, pay_day)
        if pay_date_val > today:
            continue  # skip future months

        # Determine which account to link (brokerage for most, trad_ira for BND)
        acct_for_div = trad_ira if ticker == "BND" else (roth_ira if ticker == "QQQ" else brokerage)

        # Avoid duplicates
        existing_div = await db.execute(
            select(DividendIncome).where(
                DividendIncome.organization_id == org_id,
                DividendIncome.ticker == ticker,
                DividendIncome.pay_date == pay_date_val,
            )
        )
        if existing_div.scalar_one_or_none() is None:
            div = DividendIncome(
                id=uuid.uuid4(),
                organization_id=org_id,
                account_id=acct_for_div.id,
                income_type=income_type,
                ticker=ticker,
                amount=amount,
                pay_date=pay_date_val,
                ex_date=date(current_year, month, max(1, pay_day - 10)),
                is_reinvested=False,
                currency="USD",
            )
            db.add(div)
            summary["dividends_created"] += 1

    await db.flush()
    return summary


@router.post("/seed-planning-data", response_model=Dict[str, Any])
async def seed_planning_data(
    current_user: "User" = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seed realistic planning data (holdings, tax lots, dividends, pension, etc.) for dev/test."""
    if settings.ENVIRONMENT not in ("development", "test"):
        raise HTTPException(status_code=404, detail="Not found")

    result = await seed_planning_data_internal(db, current_user)
    await db.commit()

    return {
        "message": "Planning seed data created successfully",
        **result,
    }


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
