"""Tests for Teller credential encryption."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.models.account import TellerEnrollment
from app.services.encryption_service import get_encryption_service
from app.services.teller_service import TellerService


class TestTellerEncryption:
    """Test suite for Teller credential encryption."""

    def test_encryption_service_encrypts_and_decrypts(self):
        """Should successfully encrypt and decrypt tokens."""
        encryption_service = get_encryption_service()

        plaintext_token = "test_access_token_abc123"

        # Encrypt
        encrypted = encryption_service.encrypt_token(plaintext_token)

        # Verify encrypted is different from plaintext
        assert encrypted != plaintext_token
        assert len(encrypted) > len(plaintext_token)

        # Decrypt
        decrypted = encryption_service.decrypt_token(encrypted)

        # Verify decrypted matches original
        assert decrypted == plaintext_token

    def test_encryption_service_base64_encoded(self):
        """Should return base64-encoded string suitable for TEXT columns."""
        encryption_service = get_encryption_service()

        plaintext_token = "test_token"
        encrypted = encryption_service.encrypt_token(plaintext_token)

        # Should be a string (not bytes)
        assert isinstance(encrypted, str)

        # Should be base64 (contains only alphanumeric + / + =)
        import re

        assert re.match(r"^[A-Za-z0-9+/=]+$", encrypted)

    def test_teller_enrollment_decryption(self):
        """Should decrypt access token via model method."""
        encryption_service = get_encryption_service()

        plaintext_token = "teller_access_token_xyz"
        encrypted_token = encryption_service.encrypt_token(plaintext_token)

        # Create TellerEnrollment with encrypted token
        enrollment = TellerEnrollment(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            enrollment_id="test_enrollment",
            access_token=encrypted_token,
            institution_name="Test Bank",
        )

        # Decrypt via model method
        decrypted = enrollment.get_decrypted_access_token()

        assert decrypted == plaintext_token

    @pytest.mark.asyncio
    async def test_teller_service_encrypts_on_create(self):
        """Should encrypt access token when creating enrollment."""
        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        teller_service = TellerService()

        organization_id = uuid4()
        user_id = uuid4()
        enrollment_id = "test_enrollment_123"
        plaintext_token = "plaintext_access_token"

        # Create enrollment
        enrollment = await teller_service.create_enrollment(
            db=mock_db,
            organization_id=organization_id,
            user_id=user_id,
            enrollment_id=enrollment_id,
            access_token=plaintext_token,
            institution_name="Test Bank",
        )

        # Verify access_token is encrypted (not plaintext)
        assert enrollment.access_token != plaintext_token

        # Verify can decrypt back to plaintext
        decrypted = enrollment.get_decrypted_access_token()
        assert decrypted == plaintext_token

    def test_different_tokens_encrypt_differently(self):
        """Should produce different encrypted values for different tokens."""
        encryption_service = get_encryption_service()

        token1 = "access_token_1"
        token2 = "access_token_2"

        encrypted1 = encryption_service.encrypt_token(token1)
        encrypted2 = encryption_service.encrypt_token(token2)

        # Different inputs should produce different outputs
        assert encrypted1 != encrypted2

    def test_same_token_encrypts_differently_each_time(self):
        """Should use IV/nonce so same token encrypts differently each time."""
        encryption_service = get_encryption_service()

        token = "same_token"

        encrypted1 = encryption_service.encrypt_token(token)
        encrypted2 = encryption_service.encrypt_token(token)

        # Fernet includes timestamp, so encryptions differ
        # (Protects against replay attacks)
        assert encrypted1 != encrypted2

        # But both should decrypt to same value
        assert encryption_service.decrypt_token(encrypted1) == token
        assert encryption_service.decrypt_token(encrypted2) == token

    def test_invalid_encrypted_token_raises_error(self):
        """Should raise error when trying to decrypt invalid data."""
        encryption_service = get_encryption_service()

        with pytest.raises(ValueError, match="Failed to decrypt token"):
            encryption_service.decrypt_token("not_valid_encrypted_data")

    def test_empty_token_raises_error(self):
        """Should raise error when encrypting/decrypting empty token."""
        encryption_service = get_encryption_service()

        with pytest.raises(ValueError, match="Token cannot be empty"):
            encryption_service.encrypt_token("")

        with pytest.raises(ValueError, match="Encrypted token cannot be empty"):
            encryption_service.decrypt_token("")
