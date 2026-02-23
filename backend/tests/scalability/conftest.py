"""Fixtures for scalability tests."""

import hashlib
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.transaction import Transaction
from app.models.user import User


def _dedup_hash(account_id, txn_date, amount, merchant, idx):
    """Generate a unique deduplication hash for test transactions."""
    raw = f"{account_id}|{txn_date}|{amount}|{merchant}|{idx}"
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest_asyncio.fixture
async def bulk_transactions(db_session: AsyncSession, test_user: User, test_account: Account):
    """Factory fixture that inserts N transactions with distinct merchants."""

    async def _create(n: int, *, account: Account = None) -> list[Transaction]:
        acct = account or test_account
        transactions = []
        base_date = date.today() - timedelta(days=n)
        for i in range(n):
            txn_date = base_date + timedelta(days=i)
            amount = Decimal(f"-{(i % 100) + 1}.00")
            merchant = f"Merchant_{i:04d}"
            txn = Transaction(
                id=uuid4(),
                organization_id=test_user.organization_id,
                account_id=acct.id,
                date=txn_date,
                amount=amount,
                merchant_name=merchant,
                description=f"Transaction {i}",
                category_primary="Shopping",
                is_pending=False,
                deduplication_hash=_dedup_hash(acct.id, txn_date, amount, merchant, i),
            )
            transactions.append(txn)
        db_session.add_all(transactions)
        await db_session.commit()
        return transactions

    return _create


@pytest_asyncio.fixture
async def bulk_accounts(db_session: AsyncSession, test_user: User):
    """Factory fixture that inserts N accounts."""

    async def _create(n: int) -> list[Account]:
        accounts = []
        for i in range(n):
            acct = Account(
                id=uuid4(),
                organization_id=test_user.organization_id,
                user_id=test_user.id,
                name=f"Account_{i:04d}",
                account_type=AccountType.CHECKING,
                current_balance=Decimal("1000.00"),
                is_active=True,
            )
            accounts.append(acct)
        db_session.add_all(accounts)
        await db_session.commit()
        return accounts

    return _create
