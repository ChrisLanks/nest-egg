"""Unit tests for MFAService — TOTP, backup codes, encryption."""

import pytest
import re
import time
import pyotp

from app.services.mfa_service import MFAService


svc = MFAService


class TestGenerateSecret:
    def test_returns_base32_string(self):
        secret = svc.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) >= 16


class TestVerifyTotp:
    def test_valid_code_accepted(self):
        secret = svc.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert svc.verify_totp(secret, code) is True

    def test_wrong_code_rejected(self):
        secret = svc.generate_secret()
        assert svc.verify_totp(secret, "000000") is False

    def test_window_drift_accepted(self):
        """Code from 1 window ago should still be accepted (valid_window=1)."""
        secret = svc.generate_secret()
        totp = pyotp.TOTP(secret)
        # Generate code for 30 seconds ago
        code = totp.at(time.time() - 30)
        assert svc.verify_totp(secret, code) is True


class TestBackupCodes:
    def test_generates_correct_count(self):
        codes = svc.generate_backup_codes(10)
        assert len(codes) == 10

    def test_format_xxxx_xxxx(self):
        codes = svc.generate_backup_codes(5)
        for code in codes:
            assert re.match(r"^[0-9A-F]{4}-[0-9A-F]{4}$", code), f"Bad format: {code}"

    def test_custom_count(self):
        codes = svc.generate_backup_codes(3)
        assert len(codes) == 3


class TestBackupCodeVerification:
    def test_hash_and_verify_roundtrip(self):
        codes = svc.generate_backup_codes(1)
        code = codes[0]
        hashed = svc.hash_backup_code(code)
        assert svc.verify_backup_code(code, hashed) is True

    def test_wrong_code_rejected(self):
        hashed = svc.hash_backup_code("AAAA-BBBB")
        assert svc.verify_backup_code("CCCC-DDDD", hashed) is False

    def test_verify_without_hyphen(self):
        """Codes should verify whether user enters hyphen or not."""
        code = "ABCD-EF12"
        hashed = svc.hash_backup_code(code)
        assert svc.verify_backup_code("ABCDEF12", hashed) is True

    def test_verify_with_hyphen_against_unhyphenated_hash(self):
        """Hash without hyphen, verify with hyphen."""
        hashed = svc.hash_backup_code("ABCDEF12")
        assert svc.verify_backup_code("ABCD-EF12", hashed) is True


class TestTotpUri:
    def test_uri_contains_email(self):
        secret = svc.generate_secret()
        uri = svc.get_totp_uri(secret, "user@example.com")
        assert "user@example.com" in uri or "user%40example.com" in uri

    def test_uri_contains_issuer(self):
        secret = svc.generate_secret()
        uri = svc.get_totp_uri(secret, "u@e.com", issuer="TestApp")
        assert "TestApp" in uri
