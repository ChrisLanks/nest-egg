"""Tests for data retention service."""

import hashlib
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.services.data_retention_service import DataRetentionService, _is_indefinite


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


class TestIsIndefinite:
    """Unit tests for the _is_indefinite helper — no DB needed."""

    def test_none_is_indefinite(self):
        assert _is_indefinite(None) is True

    def test_negative_one_is_indefinite(self):
        assert _is_indefinite(-1) is True

    def test_negative_large_is_indefinite(self):
        assert _is_indefinite(-999) is True

    def test_zero_is_not_indefinite(self):
        assert _is_indefinite(0) is False

    def test_positive_is_not_indefinite(self):
        assert _is_indefinite(365) is False


@pytest.mark.unit
class TestDataRetentionService:
    """Test data retention purge logic."""

    @pytest.mark.asyncio
    async def test_purge_deletes_old_transactions(self, db_session: AsyncSession, retention_setup):
        """90-day retention should delete transactions older than 90 days."""
        org_id = retention_setup["org_id"]

        result = await DataRetentionService.purge_old_data(
            db_session, org_id, retention_days=90, dry_run=False
        )

        assert isinstance(result, dict)
        assert result["transactions"] == retention_setup["old_count"]

        # Verify remaining
        count_result = await db_session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.organization_id == org_id)
        )
        remaining = count_result.scalar()
        assert remaining == retention_setup["recent_count"]

    @pytest.mark.asyncio
    async def test_dry_run_does_not_delete(self, db_session: AsyncSession, retention_setup):
        """Dry run should count but not delete."""
        org_id = retention_setup["org_id"]
        total = retention_setup["old_count"] + retention_setup["recent_count"]

        result = await DataRetentionService.purge_old_data(
            db_session, org_id, retention_days=90, dry_run=True
        )

        assert isinstance(result, dict)
        assert result["transactions"] == retention_setup["old_count"]

        # Verify nothing was actually deleted
        count_result = await db_session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.organization_id == org_id)
        )
        remaining = count_result.scalar()
        assert remaining == total

    @pytest.mark.asyncio
    async def test_no_deletion_when_all_recent(self, db_session: AsyncSession, retention_setup):
        """With a very long retention window, nothing should be deleted."""
        org_id = retention_setup["org_id"]

        result = await DataRetentionService.purge_old_data(
            db_session, org_id, retention_days=9999, dry_run=False
        )

        assert result["transactions"] == 0

    @pytest.mark.asyncio
    async def test_purge_old_data_returns_dict_with_all_keys(
        self, db_session: AsyncSession, retention_setup
    ):
        """purge_old_data must return a dict with transactions/snapshots/notifications keys."""
        org_id = retention_setup["org_id"]

        result = await DataRetentionService.purge_old_data(
            db_session, org_id, retention_days=90, dry_run=True
        )

        assert set(result.keys()) >= {"transactions", "snapshots", "notifications"}

    @pytest.mark.asyncio
    async def test_indefinite_retention_skips_purge(
        self, db_session: AsyncSession, retention_setup
    ):
        """retention_days=-1 should return zero counts without touching data."""
        org_id = retention_setup["org_id"]

        result = await DataRetentionService.purge_old_data(
            db_session, org_id, retention_days=-1, dry_run=False
        )

        assert result == {"transactions": 0, "snapshots": 0, "notifications": 0}

        # Verify all transactions still exist
        count_result = await db_session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.organization_id == org_id)
        )
        total = retention_setup["old_count"] + retention_setup["recent_count"]
        assert count_result.scalar() == total


@pytest.mark.unit
class TestDataRetentionUnitMocked:
    """Pure-unit tests using mock DB — no fixtures needed, fast."""

    def _make_db(self, scalar_value=0):
        """Build a mock AsyncSession."""
        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = scalar_value
        result.rowcount = scalar_value
        db.execute = AsyncMock(return_value=result)
        db.commit = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_purge_transactions_dry_run_returns_count(self):
        db = self._make_db(scalar_value=42)
        count = await DataRetentionService.purge_transactions(db, "org-1", 90, dry_run=True)
        assert count == 42
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_purge_transactions_live_commits(self):
        db = self._make_db(scalar_value=7)
        count = await DataRetentionService.purge_transactions(db, "org-1", 90, dry_run=False)
        assert count == 7
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_purge_audit_logs_dry_run(self):
        db = self._make_db(scalar_value=100)
        count = await DataRetentionService.purge_audit_logs(db, 365, dry_run=True)
        assert count == 100
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_purge_audit_logs_live(self):
        db = self._make_db(scalar_value=50)
        count = await DataRetentionService.purge_audit_logs(db, 365, dry_run=False)
        assert count == 50
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_gdpr_delete_user_commits(self):
        db = self._make_db(scalar_value=1)
        await DataRetentionService.gdpr_delete_user(db, str(uuid4()))
        db.commit.assert_called_once()
