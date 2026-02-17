"""Tests for account deduplication service."""

import pytest
from uuid import uuid4
import hashlib

from app.services.deduplication_service import DeduplicationService, deduplication_service
from app.models.account import Account, AccountType, AccountSource


class TestDeduplicationService:
    """Test suite for account deduplication service."""

    def test_calculate_plaid_hash_deterministic(self):
        """Should generate same hash for same inputs."""
        service = DeduplicationService()

        item_id = "item_abc123"
        account_id = "account_xyz789"

        hash1 = service.calculate_plaid_hash(item_id, account_id)
        hash2 = service.calculate_plaid_hash(item_id, account_id)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex chars
        assert isinstance(hash1, str)

    def test_calculate_plaid_hash_different_for_different_inputs(self):
        """Should generate different hashes for different inputs."""
        service = DeduplicationService()

        hash1 = service.calculate_plaid_hash("item_1", "account_1")
        hash2 = service.calculate_plaid_hash("item_2", "account_1")
        hash3 = service.calculate_plaid_hash("item_1", "account_2")

        # All three should be different
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

    def test_calculate_plaid_hash_correct_format(self):
        """Should include plaid prefix in hash calculation."""
        service = DeduplicationService()

        item_id = "item_test"
        account_id = "account_test"

        # Manually calculate expected hash
        content = f"plaid:{item_id}:{account_id}"
        expected_hash = hashlib.sha256(content.encode()).hexdigest()

        actual_hash = service.calculate_plaid_hash(item_id, account_id)

        assert actual_hash == expected_hash

    def test_calculate_manual_account_hash_with_mask(self):
        """Should generate hash using institution, type, and mask for bank accounts."""
        service = DeduplicationService()

        hash1 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "Chase Bank",
            "1234",
            "My Checking"
        )

        # Same inputs should produce same hash
        hash2 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "Chase Bank",
            "1234",
            "My Checking"
        )

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_calculate_manual_account_hash_case_insensitive(self):
        """Should normalize case for matching."""
        service = DeduplicationService()

        hash1 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "Chase Bank",
            "1234",
            "My Checking"
        )

        hash2 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "CHASE BANK",
            "1234",
            "MY CHECKING"
        )

        # Should match despite different case
        assert hash1 == hash2

    def test_calculate_manual_account_hash_whitespace_normalized(self):
        """Should normalize whitespace for matching."""
        service = DeduplicationService()

        hash1 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            " Chase Bank ",
            " 1234 ",
            " My Checking "
        )

        hash2 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "Chase Bank",
            "1234",
            "My Checking"
        )

        assert hash1 == hash2

    def test_calculate_manual_account_hash_property_type(self):
        """Should use type + name for property accounts."""
        service = DeduplicationService()

        hash1 = service.calculate_manual_account_hash(
            AccountType.PROPERTY,
            None,  # No institution for property
            None,  # No mask for property
            "123 Main St"
        )

        # Verify hash is deterministic
        hash2 = service.calculate_manual_account_hash(
            AccountType.PROPERTY,
            None,
            None,
            "123 Main St"
        )

        assert hash1 == hash2

        # Different property should have different hash
        hash3 = service.calculate_manual_account_hash(
            AccountType.PROPERTY,
            None,
            None,
            "456 Oak Ave"
        )

        assert hash1 != hash3

    def test_calculate_manual_account_hash_mortgage_type(self):
        """Should use institution + type + name for mortgage accounts."""
        service = DeduplicationService()

        hash1 = service.calculate_manual_account_hash(
            AccountType.MORTGAGE,
            "Wells Fargo",
            None,
            "Home Mortgage"
        )

        # Same mortgage at same institution should match
        hash2 = service.calculate_manual_account_hash(
            AccountType.MORTGAGE,
            "Wells Fargo",
            None,
            "Home Mortgage"
        )

        assert hash1 == hash2

        # Different institution should differ
        hash3 = service.calculate_manual_account_hash(
            AccountType.MORTGAGE,
            "Bank of America",
            None,
            "Home Mortgage"
        )

        assert hash1 != hash3

    def test_calculate_manual_account_hash_different_account_types(self):
        """Should generate different hashes for different account types."""
        service = DeduplicationService()

        hash_checking = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "Chase",
            "1234",
            "My Account"
        )

        hash_savings = service.calculate_manual_account_hash(
            AccountType.SAVINGS,
            "Chase",
            "1234",
            "My Account"
        )

        # Different account type should produce different hash
        assert hash_checking != hash_savings

    def test_deduplicate_accounts_removes_duplicates(self):
        """Should remove accounts with duplicate hashes."""
        service = DeduplicationService()

        org_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()

        duplicate_hash = "abc123"

        # Two accounts with same hash (same real-world account)
        account1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user1_id,
            name="Chase Checking",
            account_type=AccountType.CHECKING,
            plaid_item_hash=duplicate_hash,
        )

        account2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user2_id,
            name="Chase Checking",
            account_type=AccountType.CHECKING,
            plaid_item_hash=duplicate_hash,
        )

        # Unique account
        account3 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user1_id,
            name="Savings Account",
            account_type=AccountType.SAVINGS,
            plaid_item_hash="xyz789",
        )

        accounts = [account1, account2, account3]
        deduplicated = service.deduplicate_accounts(accounts)

        # Should keep only 2 accounts (first duplicate + unique)
        assert len(deduplicated) == 2
        assert account1 in deduplicated  # First duplicate kept
        assert account2 not in deduplicated  # Second duplicate removed
        assert account3 in deduplicated  # Unique account kept

    def test_deduplicate_accounts_preserves_order(self):
        """Should keep first occurrence of duplicate."""
        service = DeduplicationService()

        org_id = uuid4()
        duplicate_hash = "same_hash"

        account1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="First",
            account_type=AccountType.CHECKING,
            plaid_item_hash=duplicate_hash,
        )

        account2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Second",
            account_type=AccountType.CHECKING,
            plaid_item_hash=duplicate_hash,
        )

        account3 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Third",
            account_type=AccountType.CHECKING,
            plaid_item_hash=duplicate_hash,
        )

        accounts = [account1, account2, account3]
        deduplicated = service.deduplicate_accounts(accounts)

        # Should keep only the first one
        assert len(deduplicated) == 1
        assert deduplicated[0] == account1
        assert deduplicated[0].name == "First"

    def test_deduplicate_accounts_keeps_accounts_without_hash(self):
        """Should keep all accounts that don't have a hash."""
        service = DeduplicationService()

        org_id = uuid4()

        # Accounts without hash (manual accounts not yet hashed)
        account1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Account 1",
            account_type=AccountType.CHECKING,
            plaid_item_hash=None,
        )

        account2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Account 2",
            account_type=AccountType.SAVINGS,
            plaid_item_hash=None,
        )

        accounts = [account1, account2]
        deduplicated = service.deduplicate_accounts(accounts)

        # Should keep all accounts without hash
        assert len(deduplicated) == 2
        assert account1 in deduplicated
        assert account2 in deduplicated

    def test_deduplicate_accounts_mixed_duplicates_and_unique(self):
        """Should handle mix of duplicates and unique accounts."""
        service = DeduplicationService()

        org_id = uuid4()

        accounts = [
            # Duplicate group 1 (hash A)
            Account(id=uuid4(), organization_id=org_id, user_id=uuid4(),
                   name="Dup1-A", account_type=AccountType.CHECKING, plaid_item_hash="hashA"),
            Account(id=uuid4(), organization_id=org_id, user_id=uuid4(),
                   name="Dup1-B", account_type=AccountType.CHECKING, plaid_item_hash="hashA"),

            # Unique account 1
            Account(id=uuid4(), organization_id=org_id, user_id=uuid4(),
                   name="Unique1", account_type=AccountType.SAVINGS, plaid_item_hash="hashB"),

            # Duplicate group 2 (hash C)
            Account(id=uuid4(), organization_id=org_id, user_id=uuid4(),
                   name="Dup2-A", account_type=AccountType.CREDIT_CARD, plaid_item_hash="hashC"),
            Account(id=uuid4(), organization_id=org_id, user_id=uuid4(),
                   name="Dup2-B", account_type=AccountType.CREDIT_CARD, plaid_item_hash="hashC"),

            # Unique account 2
            Account(id=uuid4(), organization_id=org_id, user_id=uuid4(),
                   name="Unique2", account_type=AccountType.BROKERAGE, plaid_item_hash="hashD"),

            # Account without hash
            Account(id=uuid4(), organization_id=org_id, user_id=uuid4(),
                   name="NoHash", account_type=AccountType.OTHER, plaid_item_hash=None),
        ]

        deduplicated = service.deduplicate_accounts(accounts)

        # Should keep: first of each duplicate group + all unique + no hash
        # = 1 (hashA) + 1 (hashB) + 1 (hashC) + 1 (hashD) + 1 (None) = 5
        assert len(deduplicated) == 5

        names = [acc.name for acc in deduplicated]
        assert "Dup1-A" in names  # First duplicate of group 1
        assert "Dup1-B" not in names  # Second duplicate removed
        assert "Unique1" in names
        assert "Dup2-A" in names  # First duplicate of group 2
        assert "Dup2-B" not in names  # Second duplicate removed
        assert "Unique2" in names
        assert "NoHash" in names

    def test_singleton_instance(self):
        """Should provide singleton instance."""
        assert deduplication_service is not None
        assert isinstance(deduplication_service, DeduplicationService)

    def test_calculate_manual_account_hash_empty_strings(self):
        """Should handle empty strings gracefully."""
        service = DeduplicationService()

        hash1 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "",
            "",
            "Account Name"
        )

        # Should still generate a hash
        assert hash1 is not None
        assert len(hash1) == 64

    def test_edge_case_very_long_names(self):
        """Should handle very long account names."""
        service = DeduplicationService()

        long_name = "A" * 1000  # Very long name

        hash1 = service.calculate_manual_account_hash(
            AccountType.PROPERTY,
            None,
            None,
            long_name
        )

        # Should still work
        assert hash1 is not None
        assert len(hash1) == 64

    def test_edge_case_special_characters_in_names(self):
        """Should handle special characters in names."""
        service = DeduplicationService()

        special_name = "Account with $pecial Ch@rs! #123"

        hash1 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "Bank & Trust",
            "1234",
            special_name
        )

        # Should work and be deterministic
        hash2 = service.calculate_manual_account_hash(
            AccountType.CHECKING,
            "Bank & Trust",
            "1234",
            special_name
        )

        assert hash1 == hash2
        assert len(hash1) == 64
