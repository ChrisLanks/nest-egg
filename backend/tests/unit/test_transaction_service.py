"""Unit tests for transaction service."""

import pytest
from decimal import Decimal
from datetime import date

from app.services.transaction_service import TransactionService


@pytest.mark.unit
class TestTransactionService:
    """Test transaction service."""

    def test_calculate_hash(self):
        """Test transaction hash calculation for deduplication."""
        hash1 = TransactionService._calculate_hash(
            date=date(2024, 2, 15),
            amount=Decimal("-50.00"),
            merchant_name="Starbucks",
        )

        hash2 = TransactionService._calculate_hash(
            date=date(2024, 2, 15),
            amount=Decimal("-50.00"),
            merchant_name="Starbucks",
        )

        # Same transaction should have same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 char hex string

    def test_calculate_hash_different_transactions(self):
        """Test different transactions have different hashes."""
        hash1 = TransactionService._calculate_hash(
            date=date(2024, 2, 15),
            amount=Decimal("-50.00"),
            merchant_name="Starbucks",
        )

        hash2 = TransactionService._calculate_hash(
            date=date(2024, 2, 15),
            amount=Decimal("-51.00"),  # Different amount
            merchant_name="Starbucks",
        )

        assert hash1 != hash2

    def test_is_transfer_detection(self):
        """Test transfer detection logic."""
        # Positive amount = credit (not transfer by default)
        assert (
            TransactionService._is_transfer(
                amount=Decimal("100.00"),
                category="Transfer",
                merchant_name="Payment",
            )
            is True
        )

        # Negative amount with Transfer category
        assert (
            TransactionService._is_transfer(
                amount=Decimal("-100.00"),
                category="Transfer",
                merchant_name="Transfer",
            )
            is True
        )

        # Regular purchase
        assert (
            TransactionService._is_transfer(
                amount=Decimal("-50.00"),
                category="Dining",
                merchant_name="Starbucks",
            )
            is False
        )

    def test_categorize_transaction_income_vs_expense(self):
        """Test income vs expense categorization."""
        # Negative amount = expense
        assert TransactionService._categorize_income_expense(Decimal("-50.00")) == "EXPENSE"

        # Positive amount = income
        assert TransactionService._categorize_income_expense(Decimal("2000.00")) == "INCOME"

        # Zero amount
        assert TransactionService._categorize_income_expense(Decimal("0.00")) == "INCOME"

    def test_normalize_merchant_name(self):
        """Test merchant name normalization."""
        # Remove common suffixes
        assert (
            TransactionService._normalize_merchant_name("STARBUCKS #12345").lower() == "starbucks"
        )

        # Remove extra whitespace
        assert (
            TransactionService._normalize_merchant_name("  Amazon    Marketplace  ").lower()
            == "amazon marketplace"
        )

        # Handle None
        assert TransactionService._normalize_merchant_name(None) == ""

    def test_apply_category_mapping(self):
        """Test Plaid category to custom category mapping."""
        # Test exact match
        mapping = {
            "Food and Drink": "Dining",
            "Shopping": "Shopping",
        }

        assert TransactionService._apply_category_mapping("Food and Drink", mapping) == "Dining"

        # Test no match (return original)
        assert (
            TransactionService._apply_category_mapping("Unknown Category", mapping)
            == "Unknown Category"
        )

        # Test None category
        assert TransactionService._apply_category_mapping(None, mapping) is None
