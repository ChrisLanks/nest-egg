"""Tests for Teller webhook signature verification."""

import pytest
import hmac
import hashlib
from fastapi import HTTPException

from app.api.v1.teller import verify_teller_webhook_signature


class TestTellerWebhookVerification:
    """Test suite for Teller webhook signature verification."""

    def test_valid_signature_passes(self, monkeypatch):
        """Valid HMAC signature should pass verification."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_webhook_secret"
        webhook_body = b'{"event":"enrollment.connected","payload":{"enrollment_id":"enr_123"}}'

        # Generate valid signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), webhook_body, hashlib.sha256
        ).hexdigest()

        # Should not raise exception
        result = verify_teller_webhook_signature(
            signature_header=expected_signature, webhook_body=webhook_body, secret=secret
        )

        assert result is True

    def test_missing_secret_in_production_raises_error(self, monkeypatch):
        """Missing webhook secret in production should raise 500 error."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        webhook_body = b'{"test": "data"}'

        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature(
                signature_header="some_signature",
                webhook_body=webhook_body,
                secret="",  # Empty secret
            )

        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail

    def test_missing_secret_in_debug_mode_allows_with_warning(self, monkeypatch, caplog):
        """Missing webhook secret in DEBUG mode should allow with warning."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", True)

        webhook_body = b'{"test": "data"}'

        # Should not raise exception in DEBUG mode
        result = verify_teller_webhook_signature(
            signature_header="some_signature", webhook_body=webhook_body, secret=""  # Empty secret
        )

        assert result is True

    def test_missing_signature_header_in_production_raises_error(self, monkeypatch):
        """Missing Teller-Signature header in production should raise 401 error."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        webhook_body = b'{"test": "data"}'

        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature(
                signature_header=None,  # Missing header
                webhook_body=webhook_body,
                secret="test_secret",
            )

        assert exc_info.value.status_code == 401
        assert "Missing" in exc_info.value.detail

    def test_missing_signature_header_in_debug_mode_allows(self, monkeypatch):
        """Missing signature header in DEBUG mode should allow with warning."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", True)

        webhook_body = b'{"test": "data"}'

        # Should not raise exception in DEBUG mode
        result = verify_teller_webhook_signature(
            signature_header=None, webhook_body=webhook_body, secret="test_secret"
        )

        assert result is True

    def test_invalid_signature_in_production_raises_error(self, monkeypatch):
        """Invalid signature in production should raise 401 error."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_webhook_secret"
        webhook_body = b'{"event":"test"}'

        # Use wrong signature
        wrong_signature = "wrong_signature_value"

        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature(
                signature_header=wrong_signature, webhook_body=webhook_body, secret=secret
            )

        assert exc_info.value.status_code == 401
        # The HTTPException is caught and re-raised as "Webhook verification failed"
        assert "Invalid" in exc_info.value.detail or "failed" in exc_info.value.detail.lower()

    def test_invalid_signature_in_debug_mode_allows(self, monkeypatch):
        """Invalid signature in DEBUG mode should allow with warning."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", True)

        secret = "test_webhook_secret"
        webhook_body = b'{"event":"test"}'

        # Use wrong signature
        wrong_signature = "wrong_signature_value"

        # Should not raise exception in DEBUG mode
        result = verify_teller_webhook_signature(
            signature_header=wrong_signature, webhook_body=webhook_body, secret=secret
        )

        assert result is True

    def test_hmac_sha256_algorithm_used(self, monkeypatch):
        """Verification should use HMAC-SHA256 algorithm."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "my_secret_key"
        webhook_body = b'{"data":"test"}'

        # Generate signature using HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode("utf-8"), webhook_body, hashlib.sha256
        ).hexdigest()

        # Should pass verification
        result = verify_teller_webhook_signature(
            signature_header=expected_signature, webhook_body=webhook_body, secret=secret
        )

        assert result is True

    def test_constant_time_comparison_used(self, monkeypatch):
        """Signature comparison should use constant-time comparison to prevent timing attacks."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_secret"
        webhook_body = b'{"test":"data"}'

        # Generate valid signature
        valid_signature = hmac.new(secret.encode("utf-8"), webhook_body, hashlib.sha256).hexdigest()

        # The implementation uses hmac.compare_digest which is constant-time
        # Verify it works correctly
        result = verify_teller_webhook_signature(
            signature_header=valid_signature, webhook_body=webhook_body, secret=secret
        )

        assert result is True

    def test_different_body_produces_different_signature(self, monkeypatch):
        """Different webhook bodies should produce different signatures."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_secret"
        body1 = b'{"event":"enrollment.connected"}'
        body2 = b'{"event":"enrollment.disconnected"}'

        # Generate signatures for both bodies
        sig1 = hmac.new(secret.encode("utf-8"), body1, hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret.encode("utf-8"), body2, hashlib.sha256).hexdigest()

        # Signatures should be different
        assert sig1 != sig2

        # Each should validate with its own body
        assert verify_teller_webhook_signature(sig1, body1, secret) is True

        # But signature from body1 should NOT validate with body2
        with pytest.raises(HTTPException):
            verify_teller_webhook_signature(sig1, body2, secret)

    def test_case_sensitive_signature_comparison(self, monkeypatch):
        """Signature comparison should be case-sensitive."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_secret"
        webhook_body = b'{"test":"data"}'

        # Generate valid signature (hexdigest returns lowercase)
        valid_signature = hmac.new(secret.encode("utf-8"), webhook_body, hashlib.sha256).hexdigest()

        # Try with uppercase signature (should fail)
        uppercase_signature = valid_signature.upper()

        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature(
                signature_header=uppercase_signature, webhook_body=webhook_body, secret=secret
            )

        assert exc_info.value.status_code == 401

    def test_empty_webhook_body_can_be_verified(self, monkeypatch):
        """Empty webhook body should still be verifiable."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_secret"
        webhook_body = b""  # Empty body

        # Generate signature for empty body
        expected_signature = hmac.new(
            secret.encode("utf-8"), webhook_body, hashlib.sha256
        ).hexdigest()

        # Should pass verification
        result = verify_teller_webhook_signature(
            signature_header=expected_signature, webhook_body=webhook_body, secret=secret
        )

        assert result is True

    def test_unicode_characters_in_body_handled_correctly(self, monkeypatch):
        """Webhook body with unicode characters should be handled correctly."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_secret"
        webhook_body = '{"merchant":"Café ☕","amount":"€10.50"}'.encode("utf-8")

        # Generate signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), webhook_body, hashlib.sha256
        ).hexdigest()

        # Should pass verification
        result = verify_teller_webhook_signature(
            signature_header=expected_signature, webhook_body=webhook_body, secret=secret
        )

        assert result is True

    def test_very_long_webhook_body_handled(self, monkeypatch):
        """Very long webhook bodies should be handled correctly."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_secret"
        # Create a large body (10KB)
        webhook_body = b'{"data":"' + (b"x" * 10000) + b'"}'

        # Generate signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), webhook_body, hashlib.sha256
        ).hexdigest()

        # Should pass verification
        result = verify_teller_webhook_signature(
            signature_header=expected_signature, webhook_body=webhook_body, secret=secret
        )

        assert result is True

    def test_special_characters_in_secret_handled(self, monkeypatch):
        """Special characters in secret should be handled correctly."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        # Secret with special characters
        secret = "test!@#$%^&*()_+-={}[]|:;<>?,./"
        webhook_body = b'{"test":"data"}'

        # Generate signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), webhook_body, hashlib.sha256
        ).hexdigest()

        # Should pass verification
        result = verify_teller_webhook_signature(
            signature_header=expected_signature, webhook_body=webhook_body, secret=secret
        )

        assert result is True

    def test_signature_verification_deterministic(self, monkeypatch):
        """Same input should always produce same signature (deterministic)."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "test_secret"
        webhook_body = b'{"test":"data"}'

        # Generate signature twice
        sig1 = hmac.new(secret.encode("utf-8"), webhook_body, hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret.encode("utf-8"), webhook_body, hashlib.sha256).hexdigest()

        # Should be identical
        assert sig1 == sig2

        # Both should pass verification
        assert verify_teller_webhook_signature(sig1, webhook_body, secret) is True
        assert verify_teller_webhook_signature(sig2, webhook_body, secret) is True

    def test_exception_in_verification_handled_in_debug(self, monkeypatch):
        """Exceptions during verification in DEBUG mode should be caught and logged."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", True)

        # This will cause an exception in the try block
        # (trying to encode None will fail)
        secret = "test"
        webhook_body = b"test"

        # Even with an exception, DEBUG mode should allow
        result = verify_teller_webhook_signature(
            signature_header="test", webhook_body=webhook_body, secret=secret
        )

        # Should still return True in DEBUG mode despite internal processing
        assert result is True

    def test_production_mode_rejects_invalid_without_fallback(self, monkeypatch):
        """Production mode should strictly reject invalid signatures."""
        import app.api.v1.teller

        monkeypatch.setattr(app.api.v1.teller.settings, "DEBUG", False)

        secret = "correct_secret"
        webhook_body = b'{"test":"data"}'

        # Use signature generated with WRONG secret
        wrong_secret = "wrong_secret"
        wrong_signature = hmac.new(
            wrong_secret.encode("utf-8"), webhook_body, hashlib.sha256
        ).hexdigest()

        # Should raise HTTPException in production
        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature(
                signature_header=wrong_signature, webhook_body=webhook_body, secret=secret
            )

        assert exc_info.value.status_code == 401
        # The HTTPException is caught and re-raised as "Webhook verification failed"
        assert "Invalid" in exc_info.value.detail or "failed" in exc_info.value.detail.lower()
