"""Encryption service for sensitive data.

Key rotation:
  - Ciphertexts are stored with a version prefix: ``v{n}:<base64ciphertext>``
  - New writes always use ENCRYPTION_CURRENT_VERSION and MASTER_ENCRYPTION_KEY
  - Old rows (encrypted with a previous key) are decrypted via ENCRYPTION_KEY_V1
  - Legacy rows with no prefix (from before rotation was introduced) are decrypted
    with the current key (safe: they were written when that key was the only one)

Rotation procedure:
  1. Generate a new Fernet key:
       python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  2. Move current MASTER_ENCRYPTION_KEY → ENCRYPTION_KEY_V1
  3. Set MASTER_ENCRYPTION_KEY = <new key>
  4. Increment ENCRYPTION_CURRENT_VERSION (e.g. 1 → 2)
  5. Deploy — old V1 rows decrypt fine; new writes use V2 prefix
  6. Optionally re-encrypt all rows to migrate them to V2 in a one-time script
"""

import base64
from datetime import date as date_type
from cryptography.fernet import Fernet
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator
from app.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data like API tokens."""

    def __init__(self):
        """Initialize the encryption service and build the key map."""
        if not settings.MASTER_ENCRYPTION_KEY:
            raise ValueError("MASTER_ENCRYPTION_KEY must be set in environment")

        self._current_version = settings.ENCRYPTION_CURRENT_VERSION
        self._keys: dict[int, Fernet] = {}

        # Register current key at current version
        current_key = settings.MASTER_ENCRYPTION_KEY
        if isinstance(current_key, str):
            current_key = current_key.encode()
        try:
            self._keys[self._current_version] = Fernet(current_key)
        except Exception as e:
            raise ValueError(
                f"Invalid MASTER_ENCRYPTION_KEY format. Must be a valid Fernet key: {e}"
            )

        # Register previous key at V1 (for decryption-only after rotation)
        if settings.ENCRYPTION_KEY_V1 and self._current_version != 1:
            prev_key = settings.ENCRYPTION_KEY_V1
            if isinstance(prev_key, str):
                prev_key = prev_key.encode()
            try:
                self._keys[1] = Fernet(prev_key)
            except Exception as e:
                raise ValueError(
                    f"Invalid ENCRYPTION_KEY_V1 format. Must be a valid Fernet key: {e}"
                )

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token and return a versioned, base64-encoded ciphertext string.

        Format: ``v{version}:<base64(fernet_ciphertext)>``

        Args:
            token: The plaintext token to encrypt

        Returns:
            Versioned encrypted string suitable for TEXT columns
        """
        if not token:
            raise ValueError("Token cannot be empty")

        fernet = self._keys[self._current_version]
        encrypted_bytes = fernet.encrypt(token.encode())
        ciphertext = base64.b64encode(encrypted_bytes).decode("utf-8")
        return f"v{self._current_version}:{ciphertext}"

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a versioned encrypted token string.

        Handles:
        - Versioned format: ``v{n}:<ciphertext>`` — uses key for version n
        - Legacy format (no prefix): uses current key (pre-rotation rows)

        Args:
            encrypted_token: The versioned or legacy encrypted token string

        Returns:
            Decrypted plaintext token

        Raises:
            ValueError: If the token is malformed, the version is unknown, or decryption fails
        """
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")

        if not isinstance(encrypted_token, str):
            raise ValueError(
                f"decrypt_token expects a str, got {type(encrypted_token).__name__}"
            )

        # Parse version prefix
        version = self._current_version
        ciphertext = encrypted_token
        if encrypted_token.startswith("v") and ":" in encrypted_token:
            prefix, rest = encrypted_token.split(":", 1)
            try:
                version = int(prefix[1:])
                ciphertext = rest
            except (ValueError, IndexError):
                # Not a valid version prefix — treat the whole thing as legacy ciphertext
                version = self._current_version
                ciphertext = encrypted_token

        if version not in self._keys:
            raise ValueError(
                f"No decryption key configured for version {version}. "
                f"Check ENCRYPTION_KEY_V{version} in your environment."
            )

        try:
            fernet = self._keys[version]
            encrypted_bytes = base64.b64decode(ciphertext.encode("utf-8"))
            return fernet.decrypt(encrypted_bytes).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt token (version {version}): {e}")

    def encrypt_string(self, data: str) -> bytes:
        """
        Encrypt any sensitive string data using the current key.

        Args:
            data: The plaintext string to encrypt

        Returns:
            Encrypted data as bytes
        """
        if not data:
            raise ValueError("Data cannot be empty")

        fernet = self._keys[self._current_version]
        return fernet.encrypt(data.encode())

    def decrypt_string(self, encrypted_data: bytes) -> str:
        """
        Decrypt encrypted string data using the current key.

        Args:
            encrypted_data: The encrypted data bytes

        Returns:
            Decrypted data as string
        """
        if not encrypted_data:
            raise ValueError("Encrypted data cannot be empty")

        try:
            fernet = self._keys[self._current_version]
            return fernet.decrypt(encrypted_data).decode()
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


class EncryptedDate(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that transparently encrypts/decrypts date fields.

    Stored as a Text column (versioned encrypted ISO-date string); returns a
    Python ``datetime.date`` on read.  Falls back gracefully:
    - If decryption fails but the value is a valid ISO date string (YYYY-MM-DD),
      it returns the parsed date (supports legacy plaintext rows during migration).
    - Null values pass through unchanged.

    Usage in models::

        from app.services.encryption_service import EncryptedDate

        birthdate = Column(EncryptedDate, nullable=True)
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt on write: accepts date | str, stores versioned ciphertext."""
        if value is None:
            return None
        if isinstance(value, date_type):
            value = value.isoformat()
        return get_encryption_service().encrypt_token(value)

    def process_result_value(self, value, dialect):
        """Decrypt on read, return datetime.date. Falls back for legacy plaintext."""
        if value is None:
            return None
        try:
            decrypted = get_encryption_service().decrypt_token(value)
            return date_type.fromisoformat(decrypted)
        except Exception:
            # Legacy plaintext row: try parsing the raw value as ISO date
            try:
                return date_type.fromisoformat(str(value))
            except Exception:
                return None


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that transparently encrypts/decrypts string fields.

    Store as Text (versioned base64-encoded Fernet ciphertext); decrypt on read.
    During a migration window, plaintext values are returned as-is if decryption fails,
    so the model stays readable while the migration encrypts existing rows.

    Usage in models::

        from app.services.encryption_service import EncryptedString

        vehicle_vin = Column(EncryptedString, nullable=True)
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt on write."""
        if value is None:
            return None
        return get_encryption_service().encrypt_token(value)

    def process_result_value(self, value, dialect):
        """Decrypt on read. Returns plaintext as-is if decryption fails (migration safety)."""
        if value is None:
            return None
        try:
            return get_encryption_service().decrypt_token(value)
        except Exception:
            # Value is not yet encrypted (e.g. pre-migration row) — return as-is
            return value
