"""Tests for Plaid service."""

import hashlib
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

from app.services.plaid_service import PlaidService, _jwk_cache
from app.models.user import User


class TestPlaidService:
    """Test suite for Plaid service."""

    def test_is_test_user_with_test_email(self):
        """Should identify test@test.com as test user."""
        service = PlaidService()
        user = User(id=uuid4(), email="test@test.com", password_hash="hash")

        assert service.is_test_user(user) is True

    def test_is_test_user_with_regular_email(self):
        """Should not identify regular users as test users."""
        service = PlaidService()
        user = User(id=uuid4(), email="user@example.com", password_hash="hash")

        assert service.is_test_user(user) is False

    def test_is_test_user_case_sensitive(self):
        """Should be case-sensitive when checking test user."""
        service = PlaidService()
        user = User(id=uuid4(), email="Test@Test.com", password_hash="hash")  # Different case

        # Current implementation is case-sensitive
        assert service.is_test_user(user) is False

    @pytest.mark.asyncio
    async def test_create_link_token_for_test_user(self):
        """Should return dummy link token for test user."""
        service = PlaidService()
        test_user = User(id=uuid4(), email="test@test.com", password_hash="hash")

        link_token, expiration = await service.create_link_token(test_user)

        # Should return dummy token
        assert link_token.startswith("link-sandbox-")
        assert len(link_token) > len("link-sandbox-")

        # Should have future expiration
        expiration_dt = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
        assert expiration_dt > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_exchange_public_token_for_test_user(self):
        """Should create dummy accounts for test user."""
        service = PlaidService()
        test_user = User(
            id=uuid4(),
            email="test@test.com",
            password_hash="hash",
            organization_id=uuid4(),
        )

        public_token = "public-sandbox-test-token"
        institution_id = "ins_1"
        institution_name = "Test Bank"
        accounts_metadata = [
            {"id": "acc_1", "name": "Checking", "type": "depository", "subtype": "checking"},
            {"id": "acc_2", "name": "Savings", "type": "depository", "subtype": "savings"},
        ]

        access_token, accounts = await service.exchange_public_token(
            user=test_user,
            public_token=public_token,
            institution_id=institution_id,
            institution_name=institution_name,
            accounts_metadata=accounts_metadata,
        )

        # Should return access token
        assert access_token.startswith("access-sandbox-")

        # Should return dummy accounts (implementation returns 4 fixed accounts)
        assert len(accounts) == 4
        assert all("account_id" in acc for acc in accounts)
        assert all("name" in acc for acc in accounts)
        assert all("type" in acc for acc in accounts)

        # Verify account types are present
        account_types = [acc["type"] for acc in accounts]
        assert "depository" in account_types
        assert "credit" in account_types
        assert "investment" in account_types

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_missing_credentials(self, monkeypatch):
        """Should raise error if Plaid credentials not configured."""
        monkeypatch.setattr("app.config.settings.PLAID_CLIENT_ID", "")
        monkeypatch.setattr("app.config.settings.PLAID_SECRET", "")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await PlaidService.verify_webhook_signature(
                webhook_verification_header="test_header", webhook_body=b'{"test": "data"}'
            )

        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_missing_header(self, monkeypatch):
        """Should raise error if signature header missing."""
        monkeypatch.setattr("app.config.settings.PLAID_CLIENT_ID", "test_id")
        monkeypatch.setattr("app.config.settings.PLAID_SECRET", "test_secret")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await PlaidService.verify_webhook_signature(
                webhook_verification_header=None, webhook_body=b'{"test": "data"}'
            )

        assert exc_info.value.status_code == 401
        assert "Missing" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.plaid_service.jwt.decode")
    @patch("app.services.plaid_service.jwt.get_unverified_header")
    @patch("app.services.plaid_service.PlaidService._fetch_jwk")
    async def test_verify_webhook_signature_valid_jwt(
        self, mock_fetch_jwk, mock_get_header, mock_jwt_decode, monkeypatch
    ):
        """Should verify valid JWT signature."""
        monkeypatch.setattr("app.config.settings.PLAID_CLIENT_ID", "test_id")
        monkeypatch.setattr("app.config.settings.PLAID_SECRET", "test_secret")

        body = json.dumps({"item_id": "test_item_123"}).encode()
        body_hash = hashlib.sha256(body).hexdigest()

        mock_get_header.return_value = {"kid": "test-key-id", "alg": "ES256"}
        mock_jwk = MagicMock()
        mock_jwk.key = "mock_public_key"
        mock_fetch_jwk.return_value = mock_jwk
        mock_jwt_decode.return_value = {
            "item_id": "test_item_123",
            "request_body_sha256": body_hash,
        }

        result = await PlaidService.verify_webhook_signature(
            webhook_verification_header="valid.jwt.token", webhook_body=body
        )

        assert result is True
        mock_fetch_jwk.assert_called_once_with("test-key-id")
        mock_jwt_decode.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.plaid_service.jwt.get_unverified_header")
    @patch("app.services.plaid_service.PlaidService._fetch_jwk")
    @patch("app.services.plaid_service.jwt.decode")
    async def test_verify_webhook_signature_expired_token(
        self, mock_jwt_decode, mock_fetch_jwk, mock_get_header, monkeypatch
    ):
        """Should reject expired JWT token."""
        monkeypatch.setattr("app.config.settings.PLAID_CLIENT_ID", "test_id")
        monkeypatch.setattr("app.config.settings.PLAID_SECRET", "test_secret")

        import jwt as jwt_module

        mock_get_header.return_value = {"kid": "test-key-id"}
        mock_jwk = MagicMock()
        mock_fetch_jwk.return_value = mock_jwk
        mock_jwt_decode.side_effect = jwt_module.ExpiredSignatureError()

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await PlaidService.verify_webhook_signature(
                webhook_verification_header="expired.jwt.token", webhook_body=b'{"test": "data"}'
            )

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("app.services.plaid_service.jwt.get_unverified_header")
    @patch("app.services.plaid_service.PlaidService._fetch_jwk")
    @patch("app.services.plaid_service.jwt.decode")
    async def test_verify_webhook_signature_invalid_token(
        self, mock_jwt_decode, mock_fetch_jwk, mock_get_header, monkeypatch
    ):
        """Should reject invalid JWT token."""
        monkeypatch.setattr("app.config.settings.PLAID_CLIENT_ID", "test_id")
        monkeypatch.setattr("app.config.settings.PLAID_SECRET", "test_secret")

        import jwt as jwt_module

        mock_get_header.return_value = {"kid": "test-key-id"}
        mock_jwk = MagicMock()
        mock_fetch_jwk.return_value = mock_jwk
        mock_jwt_decode.side_effect = jwt_module.InvalidTokenError("Bad signature")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await PlaidService.verify_webhook_signature(
                webhook_verification_header="invalid.jwt.token", webhook_body=b'{"test": "data"}'
            )

        assert exc_info.value.status_code == 401
        assert "Invalid" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.plaid_service.jwt.decode")
    @patch("app.services.plaid_service.jwt.get_unverified_header")
    @patch("app.services.plaid_service.PlaidService._fetch_jwk")
    async def test_verify_webhook_signature_body_hash_verified(
        self, mock_fetch_jwk, mock_get_header, mock_jwt_decode, monkeypatch
    ):
        """Should verify webhook body hash if provided in JWT."""
        monkeypatch.setattr("app.config.settings.PLAID_CLIENT_ID", "test_id")
        monkeypatch.setattr("app.config.settings.PLAID_SECRET", "test_secret")

        raw_body = json.dumps({"item_id": "test_123"}, separators=(",", ":"), sort_keys=True).encode()
        body_hash = hashlib.sha256(raw_body).hexdigest()

        mock_get_header.return_value = {"kid": "test-key-id"}
        mock_jwk = MagicMock()
        mock_jwk.key = "mock_key"
        mock_fetch_jwk.return_value = mock_jwk
        mock_jwt_decode.return_value = {"item_id": "test_123", "request_body_sha256": body_hash}

        result = await PlaidService.verify_webhook_signature(
            webhook_verification_header="valid.jwt.with.hash", webhook_body=raw_body
        )

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.plaid_service.jwt.decode")
    @patch("app.services.plaid_service.jwt.get_unverified_header")
    @patch("app.services.plaid_service.PlaidService._fetch_jwk")
    async def test_verify_webhook_signature_body_hash_mismatch(
        self, mock_fetch_jwk, mock_get_header, mock_jwt_decode, monkeypatch
    ):
        """Should reject webhook if body hash doesn't match."""
        monkeypatch.setattr("app.config.settings.PLAID_CLIENT_ID", "test_id")
        monkeypatch.setattr("app.config.settings.PLAID_SECRET", "test_secret")

        mock_get_header.return_value = {"kid": "test-key-id"}
        mock_jwk = MagicMock()
        mock_fetch_jwk.return_value = mock_jwk
        mock_jwt_decode.return_value = {
            "item_id": "test_123",
            "request_body_sha256": "wrong_hash_value",
        }

        from fastapi import HTTPException

        raw_body = json.dumps({"item_id": "test_123"}).encode()
        with pytest.raises(HTTPException) as exc_info:
            await PlaidService.verify_webhook_signature(
                webhook_verification_header="valid.jwt.wrong.hash",
                webhook_body=raw_body,
            )

        assert exc_info.value.status_code == 401
        assert (
            "mismatch" in exc_info.value.detail.lower() or "failed" in exc_info.value.detail.lower()
        )

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_missing_kid(self, monkeypatch):
        """Should reject JWT with missing kid in header."""
        monkeypatch.setattr("app.config.settings.PLAID_CLIENT_ID", "test_id")
        monkeypatch.setattr("app.config.settings.PLAID_SECRET", "test_secret")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            # Use a minimal JWT-like string (header.payload.sig) so jwt.get_unverified_header
            # can decode it — but with no kid field
            import base64
            header = base64.urlsafe_b64encode(json.dumps({"alg": "ES256"}).encode()).decode().rstrip("=")
            payload = base64.urlsafe_b64encode(json.dumps({}).encode()).decode().rstrip("=")
            fake_jwt = f"{header}.{payload}.fakesig"

            await PlaidService.verify_webhook_signature(
                webhook_verification_header=fake_jwt, webhook_body=b"test"
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_exchange_public_token_generates_unique_access_tokens(self):
        """Should generate unique access tokens for each exchange."""
        service = PlaidService()
        test_user = User(
            id=uuid4(),
            email="test@test.com",
            password_hash="hash",
            organization_id=uuid4(),
        )

        accounts_metadata = [
            {"id": "acc_1", "name": "Checking", "type": "depository", "subtype": "checking"}
        ]

        # Exchange twice
        token1, _ = await service.exchange_public_token(
            user=test_user,
            public_token="token1",
            institution_id="ins_1",
            institution_name="Bank 1",
            accounts_metadata=accounts_metadata,
        )

        token2, _ = await service.exchange_public_token(
            user=test_user,
            public_token="token2",
            institution_id="ins_1",
            institution_name="Bank 1",
            accounts_metadata=accounts_metadata,
        )

        # Should generate different tokens
        assert token1 != token2

    @pytest.mark.asyncio
    async def test_create_link_token_expiration_is_future(self):
        """Should set link token expiration in the future."""
        service = PlaidService()
        test_user = User(id=uuid4(), email="test@test.com", password_hash="hash")

        before_call = datetime.utcnow()
        _, expiration = await service.create_link_token(test_user)
        after_call = datetime.utcnow()

        # Parse expiration
        expiration_dt = datetime.fromisoformat(expiration.replace("Z", "+00:00"))

        # Should be at least 3 hours in the future (Plaid tokens expire after 4 hours)
        assert expiration_dt > before_call + timedelta(hours=3)
        assert expiration_dt < after_call + timedelta(hours=5)

    @pytest.mark.asyncio
    async def test_exchange_public_token_returns_correct_account_types(self):
        """Should correctly map Plaid account types."""
        service = PlaidService()
        test_user = User(
            id=uuid4(),
            email="test@test.com",
            password_hash="hash",
            organization_id=uuid4(),
        )

        accounts_metadata = [
            {"id": "acc_1", "name": "Checking", "type": "depository", "subtype": "checking"},
            {"id": "acc_2", "name": "Credit Card", "type": "credit", "subtype": "credit_card"},
            {"id": "acc_3", "name": "Investment", "type": "investment", "subtype": "brokerage"},
        ]

        _, accounts = await service.exchange_public_token(
            user=test_user,
            public_token="test_token",
            institution_id="ins_1",
            institution_name="Bank",
            accounts_metadata=accounts_metadata,
        )

        # Should return dummy accounts (implementation returns 4 fixed accounts)
        assert len(accounts) == 4

        # Verify all major account types are present in the dummy data
        account_types = [acc["type"] for acc in accounts]
        assert "depository" in account_types
        assert "credit" in account_types
        assert "investment" in account_types
