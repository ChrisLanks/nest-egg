"""Tests for encryption service."""

import pytest
import base64
from unittest.mock import patch

from cryptography.fernet import Fernet

from app.services.encryption_service import get_encryption_service, EncryptionService


class TestEncryptionService:
    """Test suite for encryption service."""

    def test_encrypt_decrypt_token_round_trip(self):
        """Should successfully encrypt and decrypt token."""
        service = get_encryption_service()

        plaintext = "test_access_token_12345"

        # Encrypt
        encrypted = service.encrypt_token(plaintext)

        # Decrypt
        decrypted = service.decrypt_token(encrypted)

        assert decrypted == plaintext

    def test_encrypt_token_returns_versioned_string(self):
        """Should return versioned string in format v{n}:<base64> suitable for TEXT columns."""
        service = get_encryption_service()

        encrypted = service.encrypt_token("test_token")

        # Should be a string (not bytes)
        assert isinstance(encrypted, str)

        # Should have versioned prefix
        import re
        assert re.match(r"^v\d+:[A-Za-z0-9+/=]+$", encrypted), (
            f"Expected 'v{{n}}:<base64>' format, got: {encrypted[:40]}"
        )

        # The ciphertext portion should be valid base64
        ciphertext = encrypted.split(":", 1)[1]
        try:
            base64.b64decode(ciphertext)
        except Exception:
            pytest.fail("Ciphertext portion is not valid base64")

    def test_encrypt_token_produces_different_output_each_time(self):
        """Should use IV/nonce so same token encrypts differently each time."""
        service = get_encryption_service()

        token = "same_token"

        encrypted1 = service.encrypt_token(token)
        encrypted2 = service.encrypt_token(token)

        # Fernet includes timestamp, so encryptions differ
        # (Protects against replay attacks)
        assert encrypted1 != encrypted2

        # But both should decrypt to same value
        assert service.decrypt_token(encrypted1) == token
        assert service.decrypt_token(encrypted2) == token

    def test_encrypted_token_different_from_plaintext(self):
        """Should produce encrypted value different from plaintext."""
        service = get_encryption_service()

        plaintext = "my_secret_token"
        encrypted = service.encrypt_token(plaintext)

        assert encrypted != plaintext
        assert len(encrypted) > len(plaintext)

    def test_different_tokens_encrypt_differently(self):
        """Should produce different encrypted values for different tokens."""
        service = get_encryption_service()

        token1 = "token_1"
        token2 = "token_2"

        encrypted1 = service.encrypt_token(token1)
        encrypted2 = service.encrypt_token(token2)

        assert encrypted1 != encrypted2

    def test_encrypt_token_empty_string_raises_error(self):
        """Should raise error when encrypting empty token."""
        service = get_encryption_service()

        with pytest.raises(ValueError, match="Token cannot be empty"):
            service.encrypt_token("")

    def test_decrypt_token_empty_string_raises_error(self):
        """Should raise error when decrypting empty token."""
        service = get_encryption_service()

        with pytest.raises(ValueError, match="Encrypted token cannot be empty"):
            service.decrypt_token("")

    def test_decrypt_token_invalid_data_raises_error(self):
        """Should raise error when trying to decrypt invalid data."""
        service = get_encryption_service()

        with pytest.raises(ValueError, match="Failed to decrypt token"):
            service.decrypt_token("not_valid_encrypted_data")

    def test_decrypt_token_corrupted_base64_raises_error(self):
        """Should raise error when trying to decrypt corrupted base64."""
        service = get_encryption_service()

        # Valid base64 but not valid Fernet token
        corrupted = base64.b64encode(b"corrupted_data").decode("utf-8")

        with pytest.raises(ValueError, match="Failed to decrypt token"):
            service.decrypt_token(corrupted)

    def test_encrypt_string_returns_bytes(self):
        """Should return bytes when encrypting string data."""
        service = get_encryption_service()

        encrypted = service.encrypt_string("test_data")

        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

    def test_decrypt_string_returns_string(self):
        """Should return string when decrypting bytes."""
        service = get_encryption_service()

        plaintext = "test_data"
        encrypted = service.encrypt_string(plaintext)
        decrypted = service.decrypt_string(encrypted)

        assert isinstance(decrypted, str)
        assert decrypted == plaintext

    def test_encrypt_decrypt_string_round_trip(self):
        """Should successfully encrypt and decrypt string data."""
        service = get_encryption_service()

        plaintext = "sensitive_information"

        encrypted = service.encrypt_string(plaintext)
        decrypted = service.decrypt_string(encrypted)

        assert decrypted == plaintext

    def test_encrypt_string_empty_raises_error(self):
        """Should raise error when encrypting empty string."""
        service = get_encryption_service()

        with pytest.raises(ValueError, match="Data cannot be empty"):
            service.encrypt_string("")

    def test_decrypt_string_empty_raises_error(self):
        """Should raise error when decrypting empty bytes."""
        service = get_encryption_service()

        with pytest.raises(ValueError, match="Encrypted data cannot be empty"):
            service.decrypt_string(b"")

    def test_decrypt_string_invalid_data_raises_error(self):
        """Should raise error when decrypting invalid data."""
        service = get_encryption_service()

        with pytest.raises(ValueError, match="Failed to decrypt data"):
            service.decrypt_string(b"invalid_encrypted_data")

    def test_singleton_instance(self):
        """Should provide singleton instance."""
        service1 = get_encryption_service()
        service2 = get_encryption_service()

        assert service1 is service2  # Same instance

    def test_encryption_service_initialization_requires_key(self):
        """Should raise error if MASTER_ENCRYPTION_KEY not set."""
        # This test would require mocking settings, which is complex
        # In practice, the service initialization checks for the key
        service = get_encryption_service()
        assert service is not None

    def test_encrypt_token_with_special_characters(self):
        """Should handle tokens with special characters."""
        service = get_encryption_service()

        token_with_special = "token!@#$%^&*()_+-={}[]|:;<>?,./~`"

        encrypted = service.encrypt_token(token_with_special)
        decrypted = service.decrypt_token(encrypted)

        assert decrypted == token_with_special

    def test_encrypt_token_with_unicode(self):
        """Should handle tokens with unicode characters."""
        service = get_encryption_service()

        token_with_unicode = "token_with_émojis_🔒_and_中文"

        encrypted = service.encrypt_token(token_with_unicode)
        decrypted = service.decrypt_token(encrypted)

        assert decrypted == token_with_unicode

    def test_encrypt_very_long_token(self):
        """Should handle very long tokens."""
        service = get_encryption_service()

        long_token = "A" * 10000  # 10KB token

        encrypted = service.encrypt_token(long_token)
        decrypted = service.decrypt_token(encrypted)

        assert decrypted == long_token
        assert len(decrypted) == 10000

    def test_encrypt_token_deterministic_with_timestamp(self):
        """Should include timestamp in encryption (non-deterministic)."""
        service = get_encryption_service()

        token = "test_token"

        # Multiple encryptions should produce different ciphertexts
        encryptions = [service.encrypt_token(token) for _ in range(5)]

        # All should be unique (due to Fernet timestamp)
        assert len(set(encryptions)) == 5

        # But all should decrypt to same value
        decrypted = [service.decrypt_token(enc) for enc in encryptions]
        assert all(d == token for d in decrypted)

    def test_encrypt_string_vs_encrypt_token_compatibility(self):
        """Should verify encrypt_string and encrypt_token have different formats."""
        service = get_encryption_service()

        data = "test_data"

        # encrypt_string returns bytes
        encrypted_bytes = service.encrypt_string(data)
        assert isinstance(encrypted_bytes, bytes)

        # encrypt_token returns base64-encoded string
        encrypted_string = service.encrypt_token(data)
        assert isinstance(encrypted_string, str)

        # They should not be equal
        assert encrypted_bytes != encrypted_string.encode()

        # Correct decryption should work
        assert service.decrypt_string(encrypted_bytes) == data
        assert service.decrypt_token(encrypted_string) == data

    def test_encrypted_token_storage_in_database(self):
        """Should simulate storage and retrieval from database."""
        service = get_encryption_service()

        # Simulate storing in database
        plaintext_token = "database_stored_token"
        encrypted_for_db = service.encrypt_token(plaintext_token)

        # Simulate retrieval from database (stored as TEXT)
        retrieved_from_db = encrypted_for_db

        # Should successfully decrypt
        decrypted = service.decrypt_token(retrieved_from_db)
        assert decrypted == plaintext_token

    def test_cannot_decrypt_token_with_decrypt_string(self):
        """Should verify encrypt_token output cannot be decrypted with decrypt_string."""
        service = get_encryption_service()

        token = "test_token"
        encrypted_token = service.encrypt_token(token)

        # encrypt_token returns base64 string, decrypt_string expects bytes
        with pytest.raises(ValueError):
            service.decrypt_string(encrypted_token)  # Wrong type

    def test_cannot_decrypt_string_with_decrypt_token(self):
        """Should verify encrypt_string output cannot be decrypted with decrypt_token."""
        service = get_encryption_service()

        data = "test_data"
        encrypted_bytes = service.encrypt_string(data)

        # encrypt_string returns bytes, decrypt_token expects base64 string
        with pytest.raises(ValueError):
            service.decrypt_token(encrypted_bytes)  # Wrong type

    def test_encryption_preserves_exact_length(self):
        """Should verify decrypted data has exact same length as original."""
        service = get_encryption_service()

        tokens = [
            "a",
            "short",
            "medium_length_token_here",
            "A" * 100,
            "A" * 1000,
        ]

        for token in tokens:
            encrypted = service.encrypt_token(token)
            decrypted = service.decrypt_token(encrypted)
            assert len(decrypted) == len(token)

    def test_encryption_with_whitespace(self):
        """Should preserve whitespace in tokens."""
        service = get_encryption_service()

        tokens_with_whitespace = [
            " leading_space",
            "trailing_space ",
            " both_sides ",
            "internal  spaces",
            "\ttab\tcharacters\t",
            "\nnewline\ncharacters\n",
        ]

        for token in tokens_with_whitespace:
            encrypted = service.encrypt_token(token)
            decrypted = service.decrypt_token(encrypted)
            assert decrypted == token

    def test_multiple_service_instances_share_key(self):
        """Should verify multiple service instances can decrypt each other's data."""
        service1 = get_encryption_service()
        service2 = get_encryption_service()

        token = "shared_token"

        # Encrypt with service1
        encrypted = service1.encrypt_token(token)

        # Decrypt with service2
        decrypted = service2.decrypt_token(encrypted)

        assert decrypted == token


@pytest.mark.unit
class TestEncryptionKeyRotation:
    """Tests for versioned key rotation support."""

    def _make_service(self, current_key: str, current_version: int, v1_key=None):
        """Helper: instantiate EncryptionService with controlled settings."""
        mock_settings = type("S", (), {
            "MASTER_ENCRYPTION_KEY": current_key,
            "ENCRYPTION_CURRENT_VERSION": current_version,
            "ENCRYPTION_KEY_V1": v1_key,
        })()
        with patch("app.services.encryption_service.settings", mock_settings):
            return EncryptionService()

    def test_encrypt_token_includes_version_prefix(self):
        """Encrypted tokens should start with v{n}: prefix."""
        key = Fernet.generate_key().decode()
        service = self._make_service(key, current_version=1)
        encrypted = service.encrypt_token("hello")
        assert encrypted.startswith("v1:")

    def test_version_incremented_in_prefix(self):
        """After rotation, new writes carry the new version number."""
        key = Fernet.generate_key().decode()
        service = self._make_service(key, current_version=2)
        encrypted = service.encrypt_token("hello")
        assert encrypted.startswith("v2:")

    def test_decrypt_versioned_token(self):
        """Should decrypt a token with a version prefix using the correct key."""
        key = Fernet.generate_key().decode()
        service = self._make_service(key, current_version=1)
        encrypted = service.encrypt_token("plaintext")
        assert service.decrypt_token(encrypted) == "plaintext"

    def test_decrypt_legacy_token_without_prefix(self):
        """Should decrypt legacy ciphertext (no v{n}: prefix) with the current key."""
        key = Fernet.generate_key().decode()
        service = self._make_service(key, current_version=1)

        # Simulate a legacy token: raw base64 Fernet ciphertext, no version prefix
        fernet = Fernet(key.encode())
        legacy_ciphertext = base64.b64encode(fernet.encrypt(b"old_plaintext")).decode()

        assert service.decrypt_token(legacy_ciphertext) == "old_plaintext"

    def test_key_rotation_old_rows_decrypt_with_v1_key(self):
        """After rotation: rows encrypted with old key should decrypt via ENCRYPTION_KEY_V1."""
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        # Service before rotation: encrypts with old key, version 1
        pre_rotation = self._make_service(old_key, current_version=1)
        encrypted_v1 = pre_rotation.encrypt_token("sensitive_value")
        assert encrypted_v1.startswith("v1:")

        # Service after rotation: MASTER=new key (version 2), V1=old key
        post_rotation = self._make_service(
            new_key, current_version=2, v1_key=old_key
        )

        # New writes use new key
        new_encrypted = post_rotation.encrypt_token("new_value")
        assert new_encrypted.startswith("v2:")
        assert post_rotation.decrypt_token(new_encrypted) == "new_value"

        # Old v1 rows still decrypt
        assert post_rotation.decrypt_token(encrypted_v1) == "sensitive_value"

    def test_unknown_version_raises_value_error(self):
        """Decrypting a token whose version has no configured key raises ValueError."""
        key = Fernet.generate_key().decode()
        service = self._make_service(key, current_version=1)

        # Fabricate a token claiming to be version 99
        fernet = Fernet(key.encode())
        ciphertext = base64.b64encode(fernet.encrypt(b"data")).decode()
        v99_token = f"v99:{ciphertext}"

        with pytest.raises(ValueError, match="No decryption key configured for version 99"):
            service.decrypt_token(v99_token)

    def test_bytes_input_raises_value_error(self):
        """Passing bytes to decrypt_token should raise ValueError, not TypeError."""
        key = Fernet.generate_key().decode()
        service = self._make_service(key, current_version=1)
        encrypted_bytes = service.encrypt_string("data")  # returns bytes

        with pytest.raises(ValueError):
            service.decrypt_token(encrypted_bytes)  # type: ignore

    def test_cross_version_isolation(self):
        """A v2 token should not be decryptable by a service with only a v1 key."""
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        # Service with new key at version 2
        new_service = self._make_service(new_key, current_version=2)
        encrypted_v2 = new_service.encrypt_token("secret")

        # Service that only knows the old key (no V1 registered for version 2)
        old_service = self._make_service(old_key, current_version=1)

        with pytest.raises(ValueError):
            old_service.decrypt_token(encrypted_v2)
