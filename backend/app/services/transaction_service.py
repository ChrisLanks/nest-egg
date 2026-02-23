"""Transaction utility service.

Provides static helper methods for transaction processing:
deduplication hashing, transfer detection, income/expense classification,
merchant name normalization, and category mapping.
"""

import hashlib
import re
from decimal import Decimal
from datetime import date
from typing import Dict, Optional


class TransactionService:
    """Utility methods for transaction processing."""

    @staticmethod
    def _calculate_hash(
        date: date,
        amount: Decimal,
        merchant_name: str,
    ) -> str:
        """
        Generate a deduplication hash for a transaction.

        Formula: SHA256(date|amount|merchant_name)
        Returns a 64-character hex string.
        """
        hash_input = f"{date.isoformat()}|{amount}|{merchant_name or ''}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    @staticmethod
    def _is_transfer(
        amount: Decimal,
        category: Optional[str],
        merchant_name: Optional[str],
    ) -> bool:
        """
        Detect whether a transaction is a transfer between accounts.

        A transaction is considered a transfer if its category or merchant name
        contains the word "transfer" (case-insensitive), or if it is a positive
        amount with a "Payment" merchant name (credit card payment pattern).
        """
        category_lower = (category or "").lower()
        merchant_lower = (merchant_name or "").lower()

        if "transfer" in category_lower or "transfer" in merchant_lower:
            return True

        # Credit card payment pattern: positive amount with "Payment" merchant
        if amount > 0 and "payment" in merchant_lower:
            return True

        return False

    @staticmethod
    def _categorize_income_expense(amount: Decimal) -> str:
        """
        Classify a transaction as INCOME or EXPENSE based on amount sign.

        Negative amounts are expenses; zero or positive amounts are income.
        """
        return "EXPENSE" if amount < 0 else "INCOME"

    @staticmethod
    def _normalize_merchant_name(name: Optional[str]) -> str:
        """
        Normalize a merchant name by removing store numbers and extra whitespace.

        Examples:
            "STARBUCKS #12345"  → "STARBUCKS"
            "  Amazon    Marketplace  " → "Amazon Marketplace"
            None → ""
        """
        if not name:
            return ""

        # Remove common trailing store/location identifiers (#12345, store numbers)
        name = re.sub(r"\s*#\d+.*$", "", name)

        # Collapse multiple spaces and strip leading/trailing whitespace
        name = re.sub(r"\s+", " ", name).strip()

        return name

    @staticmethod
    def _apply_category_mapping(
        category: Optional[str],
        mapping: Dict[str, str],
    ) -> Optional[str]:
        """
        Map a provider category to a custom category using the given mapping.

        If the category is None or not found in the mapping, the original value
        is returned unchanged.
        """
        if category is None:
            return None
        return mapping.get(category, category)
