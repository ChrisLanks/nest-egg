"""Tests for household account deduplication service."""

import pytest
from uuid import uuid4
from decimal import Decimal

from app.services.deduplication_service import deduplication_service
from app.models.account import Account, AccountType, AccountSource


class TestHouseholdDeduplication:
    """Test suite for household account deduplication."""

    def test_deduplicate_accounts_no_duplicates(self):
        """Should return all accounts when there are no duplicates."""
        accounts = [
            Account(
                id=uuid4(),
                organization_id=uuid4(),
                user_id=uuid4(),
                name="Account 1",
                account_type=AccountType.CHECKING,
                account_source=AccountSource.PLAID,
                institution_id="chase",
                institution_name="Chase",
                mask="1234",
                current_balance=Decimal("1000.00"),
            ),
            Account(
                id=uuid4(),
                organization_id=uuid4(),
                user_id=uuid4(),
                name="Account 2",
                account_type=AccountType.SAVINGS,
                account_source=AccountSource.PLAID,
                institution_id="bofa",
                institution_name="Bank of America",
                mask="5678",
                current_balance=Decimal("2000.00"),
            ),
        ]

        result = deduplication_service.deduplicate_accounts(accounts)

        assert len(result) == 2
        assert result == accounts

    def test_deduplicate_accounts_with_exact_duplicate(self):
        """Should remove exact duplicate accounts (same institution_id and mask)."""
        org_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()

        account1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user1_id,
            name="Chase Checking (User 1)",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.PLAID,
            institution_id="ins_1",
            institution_name="Chase",
            mask="1234",
            current_balance=Decimal("1000.00"),
        )

        # Duplicate account from different user
        account2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user2_id,
            name="Chase Checking (User 2)",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.PLAID,
            institution_id="ins_1",
            institution_name="Chase",
            mask="1234",
            current_balance=Decimal("1000.00"),
        )

        accounts = [account1, account2]
        result = deduplication_service.deduplicate_accounts(accounts)

        # Should only return one account
        assert len(result) == 1
        # Should keep the first occurrence
        assert result[0].id == account1.id

    def test_deduplicate_accounts_partial_match(self):
        """Should handle accounts with same institution but different masks."""
        org_id = uuid4()

        account1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Chase Checking",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.PLAID,
            institution_id="ins_1",
            institution_name="Chase",
            mask="1234",
            current_balance=Decimal("1000.00"),
        )

        account2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Chase Savings",
            account_type=AccountType.SAVINGS,
            account_source=AccountSource.PLAID,
            institution_id="ins_1",
            institution_name="Chase",
            mask="5678",  # Different mask
            current_balance=Decimal("2000.00"),
        )

        accounts = [account1, account2]
        result = deduplication_service.deduplicate_accounts(accounts)

        # Should keep both (different masks = different accounts)
        assert len(result) == 2

    def test_deduplicate_accounts_missing_institution_id(self):
        """Should not deduplicate accounts missing institution_id."""
        org_id = uuid4()

        account1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Manual Account 1",
            account_type=AccountType.MANUAL,
            account_source=AccountSource.MANUAL,
            institution_id=None,
            institution_name="Custom Bank",
            mask="1234",
            current_balance=Decimal("1000.00"),
        )

        account2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Manual Account 2",
            account_type=AccountType.MANUAL,
            account_source=AccountSource.MANUAL,
            institution_id=None,
            institution_name="Custom Bank",
            mask="1234",  # Same mask but no institution_id
            current_balance=Decimal("1000.00"),
        )

        accounts = [account1, account2]
        result = deduplication_service.deduplicate_accounts(accounts)

        # Should keep both (can't deduplicate without institution_id)
        assert len(result) == 2

    def test_deduplicate_accounts_missing_mask(self):
        """Should not deduplicate accounts missing mask."""
        org_id = uuid4()

        account1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Investment Account 1",
            account_type=AccountType.BROKERAGE,
            account_source=AccountSource.PLAID,
            institution_id="ins_1",
            institution_name="Fidelity",
            mask=None,
            current_balance=Decimal("10000.00"),
        )

        account2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Investment Account 2",
            account_type=AccountType.BROKERAGE,
            account_source=AccountSource.PLAID,
            institution_id="ins_1",
            institution_name="Fidelity",
            mask=None,
            current_balance=Decimal("10000.00"),
        )

        accounts = [account1, account2]
        result = deduplication_service.deduplicate_accounts(accounts)

        # Should keep both (can't deduplicate without mask)
        assert len(result) == 2

    def test_deduplicate_accounts_multiple_duplicates(self):
        """Should handle multiple sets of duplicates."""
        org_id = uuid4()

        # First set of duplicates (Chase 1234)
        chase1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Chase 1 (User 1)",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.PLAID,
            institution_id="chase",
            institution_name="Chase",
            mask="1234",
            current_balance=Decimal("1000.00"),
        )

        chase2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Chase 1 (User 2)",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.PLAID,
            institution_id="chase",
            institution_name="Chase",
            mask="1234",
            current_balance=Decimal("1000.00"),
        )

        # Second set of duplicates (BofA 5678)
        bofa1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="BofA (User 1)",
            account_type=AccountType.SAVINGS,
            account_source=AccountSource.PLAID,
            institution_id="bofa",
            institution_name="Bank of America",
            mask="5678",
            current_balance=Decimal("2000.00"),
        )

        bofa2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="BofA (User 2)",
            account_type=AccountType.SAVINGS,
            account_source=AccountSource.PLAID,
            institution_id="bofa",
            institution_name="Bank of America",
            mask="5678",
            current_balance=Decimal("2000.00"),
        )

        # Unique account
        unique = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=uuid4(),
            name="Unique Account",
            account_type=AccountType.CREDIT_CARD,
            account_source=AccountSource.PLAID,
            institution_id="amex",
            institution_name="American Express",
            mask="9999",
            current_balance=Decimal("-500.00"),
        )

        accounts = [chase1, chase2, bofa1, bofa2, unique]
        result = deduplication_service.deduplicate_accounts(accounts)

        # Should deduplicate to 3 accounts (1 Chase, 1 BofA, 1 Unique)
        assert len(result) == 3

        # Verify correct accounts kept (first occurrence of each)
        account_ids = [acc.id for acc in result]
        assert chase1.id in account_ids
        assert bofa1.id in account_ids
        assert unique.id in account_ids
        assert chase2.id not in account_ids
        assert bofa2.id not in account_ids

    def test_deduplicate_accounts_empty_list(self):
        """Should handle empty account list."""
        result = deduplication_service.deduplicate_accounts([])
        assert result == []

    def test_deduplicate_accounts_single_account(self):
        """Should handle single account without issues."""
        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Single Account",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.PLAID,
            institution_id="chase",
            institution_name="Chase",
            mask="1234",
            current_balance=Decimal("1000.00"),
        )

        result = deduplication_service.deduplicate_accounts([account])

        assert len(result) == 1
        assert result[0].id == account.id
