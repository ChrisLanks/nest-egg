"""Multi-Factor Authentication service."""

import pyotp
import qrcode
import io
import secrets
from base64 import b64encode
from typing import List, Tuple, Optional
from datetime import datetime

from app.services.encryption_service import encryption_service


class MFAService:
    """Service for handling MFA operations."""

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(secret: str, email: str, issuer: str = "Nest Egg") -> str:
        """
        Generate TOTP provisioning URI for QR code.

        Args:
            secret: TOTP secret
            email: User email
            issuer: Application name

        Returns:
            Provisioning URI string
        """
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=issuer
        )

    @staticmethod
    def generate_qr_code(uri: str) -> str:
        """
        Generate QR code image as base64 string.

        Args:
            uri: TOTP provisioning URI

        Returns:
            Base64-encoded QR code image (PNG)
        """
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return b64encode(buffer.getvalue()).decode()

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """
        Verify TOTP code.

        Args:
            secret: TOTP secret
            code: 6-digit TOTP code

        Returns:
            True if code is valid
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # Allow 1 window (30 sec) drift

    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """
        Generate backup codes for MFA recovery.

        Args:
            count: Number of backup codes to generate

        Returns:
            List of backup codes (format: XXXX-XXXX)
        """
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()
            # Format as XXXX-XXXX
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)

        return codes

    @staticmethod
    def hash_backup_code(code: str) -> str:
        """
        Hash backup code for secure storage.

        Args:
            code: Backup code (with or without hyphen)

        Returns:
            Hashed backup code
        """
        # Remove hyphen for consistency
        clean_code = code.replace("-", "")

        from argon2 import PasswordHasher
        ph = PasswordHasher()
        return ph.hash(clean_code)

    @staticmethod
    def verify_backup_code(code: str, hashed_code: str) -> bool:
        """
        Verify backup code against hash.

        Args:
            code: User-provided backup code
            hashed_code: Stored hashed backup code

        Returns:
            True if code matches
        """
        clean_code = code.replace("-", "")

        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            ph.verify(hashed_code, clean_code)
            return True
        except Exception:
            return False

    @staticmethod
    def encrypt_secret(secret: str) -> str:
        """Encrypt TOTP secret for database storage."""
        return encryption_service.encrypt(secret)

    @staticmethod
    def decrypt_secret(encrypted_secret: str) -> str:
        """Decrypt TOTP secret from database."""
        return encryption_service.decrypt(encrypted_secret)

    @staticmethod
    def encrypt_backup_codes(codes: List[str]) -> str:
        """
        Encrypt and join backup codes for storage.

        Args:
            codes: List of hashed backup codes

        Returns:
            Encrypted comma-separated string
        """
        joined = ",".join(codes)
        return encryption_service.encrypt(joined)

    @staticmethod
    def decrypt_backup_codes(encrypted_codes: str) -> List[str]:
        """
        Decrypt backup codes from storage.

        Args:
            encrypted_codes: Encrypted comma-separated codes

        Returns:
            List of hashed backup codes
        """
        decrypted = encryption_service.decrypt(encrypted_codes)
        return decrypted.split(",")


mfa_service = MFAService()
