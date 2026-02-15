"""Encryption service for sensitive data."""

import base64
from cryptography.fernet import Fernet
from app.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data like API tokens."""

    def __init__(self):
        """Initialize the encryption service with the master key."""
        if not settings.MASTER_ENCRYPTION_KEY:
            raise ValueError("MASTER_ENCRYPTION_KEY must be set in environment")

        # Ensure the key is properly formatted for Fernet
        key = settings.MASTER_ENCRYPTION_KEY
        if isinstance(key, str):
            key = key.encode()

        try:
            self.cipher = Fernet(key)
        except Exception as e:
            raise ValueError(f"Invalid MASTER_ENCRYPTION_KEY format. Must be a valid Fernet key: {e}")

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token string and return as base64-encoded string for storage.

        Args:
            token: The plaintext token to encrypt

        Returns:
            Encrypted token as base64-encoded string (suitable for TEXT columns)
        """
        if not token:
            raise ValueError("Token cannot be empty")

        encrypted_bytes = self.cipher.encrypt(token.encode())
        # Base64 encode for storage in TEXT columns
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt an encrypted token from base64-encoded string.

        Args:
            encrypted_token: The base64-encoded encrypted token string

        Returns:
            Decrypted token as string
        """
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")

        try:
            # Base64 decode first
            encrypted_bytes = base64.b64decode(encrypted_token.encode('utf-8'))
            return self.cipher.decrypt(encrypted_bytes).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt token. Token may be corrupted or key changed: {e}")

    def encrypt_string(self, data: str) -> bytes:
        """
        Encrypt any sensitive string data.

        Args:
            data: The plaintext string to encrypt

        Returns:
            Encrypted data as bytes
        """
        if not data:
            raise ValueError("Data cannot be empty")

        return self.cipher.encrypt(data.encode())

    def decrypt_string(self, encrypted_data: bytes) -> str:
        """
        Decrypt encrypted string data.

        Args:
            encrypted_data: The encrypted data bytes

        Returns:
            Decrypted data as string
        """
        if not encrypted_data:
            raise ValueError("Encrypted data cannot be empty")

        try:
            return self.cipher.decrypt(encrypted_data).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {e}")


# Singleton instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """Get or create the encryption service singleton."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
