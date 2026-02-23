"""Tests for data retention service."""

import hashlib
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.services.data_retention_service import DataRetentionService


def _dedup(acct_id, d, amt, merchant, idx):
    raw = f"{acct_id}|{d}|{amt}|{merchant}|{idx}"
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest_asyncio.fixture
async def retention_setup(db_session: AsyncSession, test_user: User, test_account: Account):
    """Create a mix of old and recent transactions for retention tests."""
    old_date = date.today() - timedelta(days=200)
    recent_date = date.today() - timedelta(days=10)

    old_txns = []
    for i in range(5):
        d = old_date - timedelta(days=i)
        txn = Transaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=d,
            amount=Decimal("-10.00"),
            merchant_name=f"OldMerchant_{i}",
            description=f"Old transaction {i}",
            is_pending=False,
            deduplication_hash=_dedup(test_account.id, d, "-10.00", f"OldMerchant_{i}", i),
        )
        old_txns.append(txn)

    recent_txns = []
    for i in range(3):
        d = recent_date + timedelta(days=i)
        txn = Transaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=d,
            amount=Decimal("-20.00"),
            merchant_name=f"RecentMerchant_{i}",
            description=f"Recent transaction {i}",
            is_pending=False,
            deduplication_hash=_dedup(test_account.id, d, "-20.00", f"RecentMerchant_{i}", i + 100),
        )
        recent_txns.append(txn)

    db_session.add_all(old_txns + recent_txns)
    await db_session.commit()

    return {
        "org_id": test_user.organization_id,
        "old_count": len(old_txns),
        "recent_count": len(recent_txns),
    }


class TestDataRetentionService:
    """Test data retention purge logic."""

    @pytest.mark.asyncio
    async def test_purge_deletes_old_transactions(
        self, db_session: AsyncSession, retention_setup
    ):
        """90-day retention should delete transactions older than 90 days."""
        org_id = retention_setup["org_id"]

        deleted = await DataRetentionService.purge_old_data(
            db_session, org_id, retention_days=90, dry_run=False
        )

        assert deleted == retention_setup["old_count"]

        # Verify remaining
        result = await db_session.execute(
            select(func.count()).select_from(Transaction).where(
                Transaction.organization_id == org_id
            )
        )
        remaining = result.scalar()
        assert remaining == retention_setup["recent_count"]

    @pytest.mark.asyncio
    async def test_dry_run_does_not_delete(
        self, db_session: AsyncSession, retention_setup
    ):
        """Dry run should count but not delete."""
        org_id = retention_setup["org_id"]
        total = retention_setup["old_count"] + retention_setup["recent_count"]

        would_delete = await DataRetentionService.purge_old_data(
            db_session, org_id, retention_days=90, dry_run=True
        )

        assert would_delete == retention_setup["old_count"]

        # Verify nothing was actually deleted
        result = await db_session.execute(
            select(func.count()).select_from(Transaction).where(
                Transaction.organization_id == org_id
            )
        )
        remaining = result.scalar()
        assert remaining == total

    @pytest.mark.asyncio
    async def test_no_deletion_when_all_recent(
        self, db_session: AsyncSession, retention_setup
    ):
        """With a very long retention window, nothing should be deleted."""
        org_id = retention_setup["org_id"]

        deleted = await DataRetentionService.purge_old_data(
            db_session, org_id, retention_days=9999, dry_run=False
        )

        assert deleted == 0
