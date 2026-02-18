"""Unit tests for authentication service."""

import pytest
from datetime import timedelta

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token


@pytest.mark.unit
class TestAuthService:
    """Test authentication service."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = "test-user-id"
        token = create_access_token(user_id=user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "test-user-id"
        token = create_refresh_token(user_id=user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        user_id = "test-user-id"
        token = auth_service.create_access_token(user_id=user_id)

        payload = auth_service.verify_token(token)
        assert payload is not None
        assert payload.get("sub") == user_id

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"

        payload = auth_service.verify_token(invalid_token)
        assert payload is None

    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        user_id = "test-user-id"
        token = auth_service.create_access_token(
            user_id=user_id,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        payload = auth_service.verify_token(token)
        assert payload is None
