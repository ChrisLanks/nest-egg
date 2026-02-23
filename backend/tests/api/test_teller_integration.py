"""Integration tests for Teller API endpoints and service."""

import pytest
from fastapi import status
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import date
from uuid import uuid4

from app.models.account import TellerEnrollment, Account, AccountSource, AccountType
from app.services.teller_service import TellerService

pytestmark = pytest.mark.asyncio


class TestTellerService:
    """Test suite for Teller service integration."""

    async def test_create_enrollment_encrypts_access_token(self, db, test_user):
        """Should encrypt access token when creating enrollment."""
        service = TellerService()

        plaintext_token = "test_access_token_12345"
        enrollment_id = "enr_test123"

        enrollment = await service.create_enrollment(
            db=db,
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id=enrollment_id,
            access_token=plaintext_token,
            institution_name="Test Bank",
        )

        # Access token should be encrypted (not plaintext)
        assert enrollment.access_token != plaintext_token

        # Should be able to decrypt back to plaintext
        decrypted = enrollment.get_decrypted_access_token()
        assert decrypted == plaintext_token

    async def test_sync_accounts_creates_new_accounts(self, db, test_user):
        """Should create new accounts from Teller API."""
        from app.services.encryption_service import get_encryption_service

        service = TellerService()
        encrypted_token = get_encryption_service().encrypt_token("test_token")

        # Create enrollment
        enrollment = TellerEnrollment(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id="enr_test",
            access_token=encrypted_token,
            institution_name="Test Bank",
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        # Mock Teller API response
        mock_accounts_data = [
            {
                "id": "acc_123",
                "name": "Checking Account",
                "type": "depository",
                "last_four": "1234",
                "institution": {"name": "Test Bank"},
                "balance": {"available": 1000.50},
            },
            {
                "id": "acc_456",
                "name": "Savings Account",
                "type": "depository",
                "last_four": "5678",
                "institution": {"name": "Test Bank"},
                "balance": {"available": 5000.00},
            },
        ]

        with patch.object(service, "_make_request", return_value=mock_accounts_data):
            accounts = await service.sync_accounts(db, enrollment)

        # Should create 2 accounts
        assert len(accounts) == 2
        assert accounts[0].name == "Checking Account"
        assert accounts[1].name == "Savings Account"
        assert accounts[0].account_source == AccountSource.TELLER
        assert accounts[1].account_source == AccountSource.TELLER

    async def test_sync_accounts_updates_existing_balances(self, db, test_user):
        """Should update balances for existing accounts."""
        from app.services.encryption_service import get_encryption_service

        service = TellerService()
        encrypted_token = get_encryption_service().encrypt_token("test_token")

        # Create enrollment
        enrollment = TellerEnrollment(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id="enr_test",
            access_token=encrypted_token,
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        # Create existing account
        existing_account = Account(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            teller_enrollment_id=enrollment.id,
            external_account_id="acc_123",
            name="Checking",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.TELLER,
            current_balance=Decimal("1000.00"),
        )
        db.add(existing_account)
        await db.commit()

        # Mock API with updated balance
        mock_accounts_data = [
            {
                "id": "acc_123",
                "name": "Checking",
                "type": "depository",
                "balance": {"available": 2000.50},
            }
        ]

        with patch.object(service, "_make_request", return_value=mock_accounts_data):
            accounts = await service.sync_accounts(db, enrollment)

        # Should update existing account balance
        assert len(accounts) == 1
        assert accounts[0].id == existing_account.id
        assert accounts[0].current_balance == Decimal("2000.50")

    async def test_sync_transactions_creates_new_transactions(self, db, test_user, test_account):
        """Should create new transactions from Teller API."""
        from app.services.encryption_service import get_encryption_service

        service = TellerService()
        encrypted_token = get_encryption_service().encrypt_token("test_token")

        # Create Teller enrollment and link to account
        enrollment = TellerEnrollment(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id="enr_test",
            access_token=encrypted_token,
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        # Update test_account to have Teller enrollment
        test_account.teller_enrollment_id = enrollment.id
        test_account.external_account_id = "acc_123"
        await db.commit()

        # Mock Teller API transaction response
        mock_transactions_data = [
            {
                "id": "txn_1",
                "date": "2024-01-15T00:00:00Z",
                "amount": "-50.00",
                "description": "Starbucks",
                "details": {
                    "category": "food_and_drink",
                    "counterparty": {"name": "Starbucks Coffee"},
                },
                "status": "posted",
            },
            {
                "id": "txn_2",
                "date": "2024-01-14T00:00:00Z",
                "amount": "-25.50",
                "description": "Gas Station",
                "details": {"category": "transportation", "counterparty": {"name": "Shell Gas"}},
                "status": "posted",
            },
        ]

        with patch.object(service, "_make_request", return_value=mock_transactions_data):
            transactions = await service.sync_transactions(db, test_account)

        # Should create 2 transactions
        assert len(transactions) == 2
        assert transactions[0].merchant_name == "Starbucks Coffee"
        assert transactions[1].merchant_name == "Shell Gas"
        assert transactions[0].amount == Decimal("-50.00")

    async def test_sync_transactions_deduplication(self, db, test_user, test_account):
        """Should not create duplicate transactions."""
        from app.models.transaction import Transaction
        from app.services.encryption_service import get_encryption_service

        service = TellerService()
        encrypted_token = get_encryption_service().encrypt_token("test_token")

        # Create enrollment and link
        enrollment = TellerEnrollment(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id="enr_test",
            access_token=encrypted_token,
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        test_account.teller_enrollment_id = enrollment.id
        test_account.external_account_id = "acc_123"
        await db.commit()

        # Create existing transaction with deduplication_hash
        existing_txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            external_transaction_id="txn_1",
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
            merchant_name="Starbucks",
            deduplication_hash=str(uuid4()),
        )
        db.add(existing_txn)
        await db.commit()

        # Mock API returning same transaction
        mock_transactions_data = [
            {
                "id": "txn_1",  # Same ID as existing
                "date": "2024-01-15T00:00:00Z",
                "amount": "-50.00",
                "description": "Starbucks",
                "details": {"category": "food", "counterparty": {"name": "Starbucks"}},
                "status": "posted",
            }
        ]

        with patch.object(service, "_make_request", return_value=mock_transactions_data):
            transactions = await service.sync_transactions(db, test_account)

        # Should not create duplicate
        assert len(transactions) == 0

    async def test_map_account_type_correctly(self):
        """Should map Teller account types to internal AccountType."""
        service = TellerService()

        assert service._map_account_type("depository") == AccountType.CHECKING
        assert service._map_account_type("credit") == AccountType.CREDIT_CARD
        assert service._map_account_type("loan") == AccountType.LOAN
        assert service._map_account_type("investment") == AccountType.BROKERAGE
        assert service._map_account_type("unknown") == AccountType.OTHER

    async def test_generate_dedup_hash_deterministic(self, test_account):
        """Should generate deterministic hash for transaction deduplication."""
        service = TellerService()

        txn_data = {
            "id": "txn_123",
            "date": "2024-01-15",
            "amount": "-50.00",
            "description": "Test Merchant",
        }

        hash1 = service._generate_dedup_hash(test_account.id, txn_data)
        hash2 = service._generate_dedup_hash(test_account.id, txn_data)

        # Should be deterministic
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 length


class TestTellerWebhookHandling:
    """Test suite for Teller webhook endpoints."""

    @pytest.mark.skip(
        reason="Rate limiting is bypassed in development (ENVIRONMENT=development) "
               "and requires a live Redis instance; cannot be exercised in the test suite."
    )
    async def test_webhook_requires_rate_limiting(self, async_client):
        """Should enforce rate limiting on webhook endpoint."""
        from app.services.rate_limit_service import rate_limit_service

        webhook_data = {"event": "enrollment.connected", "payload": {"enrollment_id": "enr_test"}}

        # Reset rate limit before test to ensure clean state
        await rate_limit_service.reset_rate_limit("127.0.0.1", "/api/v1/teller/webhook")

        # Make more requests than rate limit allows (20/minute)
        for i in range(25):
            response = await async_client.post("/api/v1/teller/webhook", json=webhook_data)

            if i < 20:
                # First 20 should succeed (or fail for other reasons)
                assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
            else:
                # After 20, should be rate limited
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                break

    async def test_webhook_enrollment_connected(self, async_client, db, test_user):
        """Should handle enrollment.connected webhook."""
        # Create enrollment
        enrollment = TellerEnrollment(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id="enr_test123",
            access_token="encrypted",
            institution_name="Test Bank",
        )
        db.add(enrollment)
        await db.commit()

        webhook_data = {
            "event": "enrollment.connected",
            "payload": {"enrollment_id": "enr_test123"},
        }

        with patch("app.services.rate_limit_service.RateLimitService.check_rate_limit", new_callable=AsyncMock):
            response = await async_client.post("/api/v1/teller/webhook", json=webhook_data)

        # Should acknowledge webhook
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "acknowledged"

    async def test_webhook_transaction_posted_triggers_sync(
        self, async_client, db, test_user, test_account
    ):
        """Should trigger transaction sync on transaction.posted webhook."""
        # Create enrollment
        enrollment = TellerEnrollment(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id="enr_test",
            access_token="encrypted",
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        # Link account to enrollment
        test_account.teller_enrollment_id = enrollment.id
        test_account.external_account_id = "acc_123"
        await db.commit()

        webhook_data = {
            "event": "transaction.posted",
            "payload": {"enrollment_id": "enr_test", "account_id": "acc_123"},
        }

        with patch("app.services.rate_limit_service.RateLimitService.check_rate_limit", new_callable=AsyncMock), \
             patch("app.api.v1.teller.get_teller_service") as mock_get_service:
            mock_teller = AsyncMock()
            mock_get_service.return_value = mock_teller

            response = await async_client.post("/api/v1/teller/webhook", json=webhook_data)

            # Should trigger sync
            assert response.status_code == status.HTTP_200_OK
            # Verify sync was called
            mock_teller.sync_transactions.assert_called_once()

    async def test_webhook_unknown_enrollment_returns_not_found(self, async_client):
        """Should handle webhook for unknown enrollment gracefully."""
        webhook_data = {
            "event": "enrollment.connected",
            "payload": {"enrollment_id": "nonexistent"},
        }

        with patch("app.services.rate_limit_service.RateLimitService.check_rate_limit", new_callable=AsyncMock):
            response = await async_client.post("/api/v1/teller/webhook", json=webhook_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "enrollment_not_found"


class TestTellerErrorHandling:
    """Test error handling for Teller integration."""

    async def test_sync_handles_api_timeout(self, db, test_user):
        """Should handle API timeout gracefully."""
        service = TellerService()

        enrollment = TellerEnrollment(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id="enr_test",
            access_token="encrypted",
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        # Mock timeout
        with patch.object(service, "_make_request", side_effect=TimeoutError("Request timeout")):
            with pytest.raises(Exception):
                await service.sync_accounts(db, enrollment)

    async def test_sync_handles_invalid_credentials(self, db, test_user):
        """Should handle invalid credentials error."""
        service = TellerService()

        enrollment = TellerEnrollment(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            enrollment_id="enr_test",
            access_token="invalid_encrypted_token",
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        # Mock 401 Unauthorized
        mock_error = MagicMock()
        mock_error.status_code = 401

        with patch.object(service, "_make_request", side_effect=Exception("Unauthorized")):
            with pytest.raises(Exception):
                await service.sync_accounts(db, enrollment)
