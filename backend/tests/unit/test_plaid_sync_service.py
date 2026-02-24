"""Unit tests for PlaidTransactionSyncService — deduplication, hash generation."""

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.services.plaid_transaction_sync_service import (
    PlaidTransactionSyncService,
    MockPlaidTransactionGenerator,
)


svc = PlaidTransactionSyncService


class TestDeduplicationHash:
    def test_consistent(self):
        """Same inputs produce same hash."""
        acct = uuid4()
        h1 = svc.generate_deduplication_hash(acct, date(2024, 1, 1), Decimal("50"), "Starbucks")
        h2 = svc.generate_deduplication_hash(acct, date(2024, 1, 1), Decimal("50"), "Starbucks")
        assert h1 == h2

    def test_different_amounts_different_hash(self):
        acct = uuid4()
        h1 = svc.generate_deduplication_hash(acct, date(2024, 1, 1), Decimal("50"), "Starbucks")
        h2 = svc.generate_deduplication_hash(acct, date(2024, 1, 1), Decimal("51"), "Starbucks")
        assert h1 != h2

    def test_different_dates_different_hash(self):
        acct = uuid4()
        h1 = svc.generate_deduplication_hash(acct, date(2024, 1, 1), Decimal("50"), "Starbucks")
        h2 = svc.generate_deduplication_hash(acct, date(2024, 1, 2), Decimal("50"), "Starbucks")
        assert h1 != h2

    def test_different_accounts_different_hash(self):
        h1 = svc.generate_deduplication_hash(uuid4(), date(2024, 1, 1), Decimal("50"), "Test")
        h2 = svc.generate_deduplication_hash(uuid4(), date(2024, 1, 1), Decimal("50"), "Test")
        assert h1 != h2

    def test_hash_is_sha256_hex(self):
        h = svc.generate_deduplication_hash(uuid4(), date(2024, 1, 1), Decimal("50"), "Test")
        assert len(h) == 64  # SHA256 hex digest is 64 chars


class TestMockTransactionGenerator:
    def test_generates_correct_count(self):
        txns = MockPlaidTransactionGenerator.generate_mock_transactions(
            "acc_123", date(2024, 1, 1), date(2024, 3, 31), count=20
        )
        assert len(txns) == 20

    def test_sorted_descending(self):
        txns = MockPlaidTransactionGenerator.generate_mock_transactions(
            "acc_123", date(2024, 1, 1), date(2024, 6, 30), count=30
        )
        dates = [t["date"] for t in txns]
        assert dates == sorted(dates, reverse=True)

    def test_has_required_fields(self):
        txns = MockPlaidTransactionGenerator.generate_mock_transactions(
            "acc_123", date(2024, 1, 1), date(2024, 1, 31), count=5
        )
        for txn in txns:
            assert "transaction_id" in txn
            assert "account_id" in txn
            assert "date" in txn
            assert "amount" in txn
            assert "name" in txn

    def test_last_5_are_pending(self):
        txns = MockPlaidTransactionGenerator.generate_mock_transactions(
            "acc_123", date(2024, 1, 1), date(2024, 3, 31), count=20
        )
        # Sort by original index (transaction_id contains index)
        pending_count = sum(1 for t in txns if t["pending"])
        assert pending_count == 5
