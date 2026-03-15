"""Unit tests for development API endpoints."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.dev import (
    debug_transactions,
    generate_deduplication_hash,
    seed_mock_data,
    seed_mock_data_internal,
)
from app.models.user import User


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.mark.unit
class TestGenerateDeduplicationHash:
    """Tests for the deduplication hash helper."""

    @pytest.mark.asyncio
    async def test_generates_consistent_hash(self):
        """Same inputs should produce the same hash."""
        account_id = uuid4()
        d = date(2024, 6, 15)
        amount = Decimal("45.32")
        merchant = "Whole Foods Market"

        hash1 = await generate_deduplication_hash(account_id, d, amount, merchant)
        hash2 = await generate_deduplication_hash(account_id, d, amount, merchant)

        assert hash1 == hash2
        assert len(hash1) == 16

    @pytest.mark.asyncio
    async def test_different_inputs_produce_different_hash(self):
        """Different inputs should produce different hashes."""
        account_id = uuid4()
        d = date(2024, 6, 15)

        hash1 = await generate_deduplication_hash(account_id, d, Decimal("45.32"), "Starbucks")
        hash2 = await generate_deduplication_hash(account_id, d, Decimal("12.00"), "Target")

        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_negative_amount_uses_abs(self):
        """Negative and positive amounts should produce the same hash."""
        account_id = uuid4()
        d = date(2024, 6, 15)
        merchant = "Amazon"

        hash_pos = await generate_deduplication_hash(account_id, d, Decimal("99.99"), merchant)
        hash_neg = await generate_deduplication_hash(account_id, d, Decimal("-99.99"), merchant)

        assert hash_pos == hash_neg


@pytest.mark.unit
class TestDebugTransactions:
    """Tests for GET /dev/debug-transactions."""

    @pytest.mark.asyncio
    @patch("app.api.v1.dev.settings")
    async def test_blocks_in_production(self, mock_settings, mock_user, mock_db):
        """Should return 404 in production environment."""
        mock_settings.ENVIRONMENT = "production"

        with pytest.raises(HTTPException) as exc_info:
            await debug_transactions(current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.dev.settings")
    async def test_allowed_in_development(self, mock_settings, mock_user, mock_db):
        """Should return data in development environment."""
        mock_settings.ENVIRONMENT = "development"

        # Mock db.execute for the three queries (count txns, count accts, sample txns)
        mock_txn_count = Mock()
        mock_txn_count.scalar.return_value = 10

        mock_acc_count = Mock()
        mock_acc_count.scalar.return_value = 2

        mock_txns_result = Mock()
        mock_txns_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_txn_count, mock_acc_count, mock_txns_result]

        result = await debug_transactions(current_user=mock_user, db=mock_db)

        assert result["user_email"] == mock_user.email
        assert result["transaction_count"] == 10
        assert result["account_count"] == 2
        assert result["sample_transactions"] == []

    @pytest.mark.asyncio
    @patch("app.api.v1.dev.settings")
    async def test_allowed_in_staging(self, mock_settings, mock_user, mock_db):
        """Should return data in staging environment."""
        mock_settings.ENVIRONMENT = "staging"

        mock_txn_count = Mock()
        mock_txn_count.scalar.return_value = 0

        mock_acc_count = Mock()
        mock_acc_count.scalar.return_value = 0

        mock_txns_result = Mock()
        mock_txns_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_txn_count, mock_acc_count, mock_txns_result]

        result = await debug_transactions(current_user=mock_user, db=mock_db)

        assert result["transaction_count"] == 0


@pytest.mark.unit
class TestSeedMockData:
    """Tests for POST /dev/seed-mock-data."""

    @pytest.mark.asyncio
    @patch("app.api.v1.dev.settings")
    async def test_blocks_in_production(self, mock_settings, mock_user, mock_db):
        """Should return 404 in production environment."""
        mock_settings.ENVIRONMENT = "production"

        with pytest.raises(HTTPException) as exc_info:
            await seed_mock_data(current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 404
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.api.v1.dev.get_category_id_for_plaid_category", new_callable=AsyncMock)
    @patch("app.api.v1.dev.settings")
    async def test_seeds_data_in_development(self, mock_settings, mock_get_cat, mock_user, mock_db):
        """Should seed mock data and commit in development."""
        mock_settings.ENVIRONMENT = "development"
        mock_get_cat.return_value = None

        result = await seed_mock_data(current_user=mock_user, db=mock_db)

        assert result["message"] == "Mock data seeded successfully"
        assert result["accounts_created"] == 2
        assert result["transactions_created"] == 25
        mock_db.commit.assert_awaited_once()


@pytest.mark.unit
class TestSeedMockDataInternal:
    """Tests for the internal seed_mock_data_internal function."""

    @pytest.mark.asyncio
    @patch("app.api.v1.dev.get_category_id_for_plaid_category", new_callable=AsyncMock)
    async def test_creates_accounts_and_transactions(self, mock_get_cat, mock_user, mock_db):
        """Should create 2 accounts and 25 transactions."""
        mock_get_cat.return_value = None

        result = await seed_mock_data_internal(mock_db, mock_user)

        assert result["accounts_created"] == 2
        assert result["transactions_created"] == 25
        # Two accounts flushed
        assert mock_db.flush.await_count == 2
        # 2 accounts + 25 transactions = 27 add calls
        assert mock_db.add.call_count == 27
