"""
Security test: Metrics endpoint credential hardening.

Two gaps existed in the metrics credential validation:

1. config.py validate_metrics_password only blocked the exact string
   "metrics_admin" — not short passwords or other common weak values like
   "abc", "password123", or "admin".  An operator who set METRICS_PASSWORD=abc
   would pass the validator and expose the metrics endpoint with a 3-char
   password in production.

2. METRICS_USERNAME defaulted to "admin" with NO validator at all — a
   trivially guessable username that halves the entropy of the credential pair.

3. secrets_validation_service metrics check used a 4-item hardcoded list
   instead of the existing _is_default_or_weak() helper, so most weak values
   were silently accepted.

Fixes:
- validate_metrics_password now enforces len >= 16 AND rejects known-weak
  values in non-development environments.
- validate_metrics_username (new) rejects "admin", "metrics", "prometheus"
  in non-development environments.
- secrets_validation_service uses _is_default_or_weak() + len >= 16 check
  and adds a metrics_username_changed checklist entry.
"""

import os
from unittest.mock import patch

import pytest

from app.services.secrets_validation_service import SecretsValidationService


# ---------------------------------------------------------------------------
# Helpers — FakeSettings pattern (same approach as existing unit tests)
# ---------------------------------------------------------------------------


def _make_fake_settings(**overrides):
    """Build a FakeSettings with safe production defaults, overridable per-test."""

    class FakeSettings:
        pass

    s = FakeSettings()
    s.DEBUG = overrides.get("DEBUG", False)
    s.SECRET_KEY = overrides.get("SECRET_KEY", "k8X9mZp2qR7wN4vB6cD1fG3hJ5kL0mNx")  # pragma: allowlist secret
    s.DATABASE_URL = overrides.get(
        "DATABASE_URL",
        "postgresql://u:X9kQ!mZ2vL8nR4wY@db:5432/prod",  # pragma: allowlist secret
    )
    s.MASTER_ENCRYPTION_KEY = overrides.get("MASTER_ENCRYPTION_KEY", "a" * 32)
    s.CORS_ORIGINS = overrides.get("CORS_ORIGINS", ["https://app.example.com"])
    s.ALLOWED_HOSTS = overrides.get("ALLOWED_HOSTS", ["app.example.com"])
    s.PLAID_CLIENT_ID = overrides.get("PLAID_CLIENT_ID", "plaid_client_id_val")
    s.PLAID_SECRET = overrides.get("PLAID_SECRET", "plaid_secret_val")
    s.PLAID_WEBHOOK_SECRET = overrides.get("PLAID_WEBHOOK_SECRET", "webhook_val")
    s.METRICS_PASSWORD = overrides.get("METRICS_PASSWORD", "xK9mP2qL7nR4wZ8v")  # 16 chars  # pragma: allowlist secret
    s.METRICS_USERNAME = overrides.get("METRICS_USERNAME", "metrics_reader")
    return s


# ---------------------------------------------------------------------------
# config.py validators — tested by calling them directly
# (avoids constructing the full Settings object which reads env vars)
# ---------------------------------------------------------------------------


class TestMetricsPasswordConfigValidator:
    """validate_metrics_password must enforce length and known-weak values."""

    def _call_validator(self, password: str, env: str) -> str:
        """Invoke the field_validator by accessing the underlying function via __dict__."""
        from app.config import Settings

        fn = Settings.__dict__["validate_metrics_password"].__wrapped__
        with patch.dict(os.environ, {"ENVIRONMENT": env}):
            return fn(Settings, password)

    def test_exact_default_blocked_in_production(self):
        from pydantic import ValidationError
        with pytest.raises((ValueError, Exception), match="Insecure METRICS_PASSWORD"):
            self._call_validator("metrics_admin", "production")

    def test_short_password_blocked_in_production(self):
        with pytest.raises((ValueError, Exception), match="Insecure METRICS_PASSWORD"):
            self._call_validator("abc", "production")

    def test_15_char_password_blocked_in_production(self):
        with pytest.raises((ValueError, Exception), match="Insecure METRICS_PASSWORD"):
            self._call_validator("a" * 15, "production")

    def test_known_weak_values_blocked_in_production(self):
        for weak in ("password", "admin", "changeme", "secret", "123456", "qwerty"):
            with pytest.raises((ValueError, Exception), match="Insecure METRICS_PASSWORD"):
                self._call_validator(weak, "production")

    def test_strong_password_accepted_in_production(self):
        result = self._call_validator("xK9mP2qL7nR4wZ8v", "production")  # pragma: allowlist secret
        assert result == "xK9mP2qL7nR4wZ8v"  # pragma: allowlist secret

    def test_16_char_boundary_accepted(self):
        result = self._call_validator("abcdefghijklmnop", "production")
        assert len(result) == 16

    def test_weak_password_allowed_in_development(self):
        result = self._call_validator("metrics_admin", "development")
        assert result == "metrics_admin"

    def test_weak_password_allowed_in_test_environment(self):
        result = self._call_validator("short", "test")
        assert result == "short"


class TestMetricsUsernameConfigValidator:
    """validate_metrics_username must reject default/guessable usernames in prod."""

    def _call_validator(self, username: str, env: str) -> str:
        from app.config import Settings

        fn = Settings.__dict__["validate_metrics_username"].__wrapped__
        with patch.dict(os.environ, {"ENVIRONMENT": env}):
            return fn(Settings, username)

    def test_admin_blocked_in_production(self):
        with pytest.raises((ValueError, Exception), match="Insecure default METRICS_USERNAME"):
            self._call_validator("admin", "production")

    def test_metrics_blocked_in_production(self):
        with pytest.raises((ValueError, Exception), match="Insecure default METRICS_USERNAME"):
            self._call_validator("metrics", "production")

    def test_prometheus_blocked_in_production(self):
        with pytest.raises((ValueError, Exception), match="Insecure default METRICS_USERNAME"):
            self._call_validator("prometheus", "production")

    def test_custom_username_accepted_in_production(self):
        result = self._call_validator("metrics_reader", "production")
        assert result == "metrics_reader"

    def test_default_username_allowed_in_development(self):
        result = self._call_validator("admin", "development")
        assert result == "admin"

    def test_default_username_allowed_in_test(self):
        result = self._call_validator("admin", "test")
        assert result == "admin"


# ---------------------------------------------------------------------------
# secrets_validation_service — production validation and checklist
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSecretsValidationServiceMetricsPassword:
    """validate_production_secrets must catch weak/short metrics passwords."""

    def test_short_metrics_password_flagged(self):
        fake = _make_fake_settings(METRICS_PASSWORD="abc")
        with patch("app.services.secrets_validation_service.settings", fake):
            result = SecretsValidationService.validate_production_secrets()
        assert any("METRICS_PASSWORD" in e for e in result["errors"])

    def test_weak_metrics_password_flagged(self):
        for weak in ("admin", "password", "metrics_admin", "changeme"):
            fake = _make_fake_settings(METRICS_PASSWORD=weak)
            with patch("app.services.secrets_validation_service.settings", fake):
                result = SecretsValidationService.validate_production_secrets()
            assert any("METRICS_PASSWORD" in e for e in result["errors"]), (
                f"Expected {weak!r} to be flagged"
            )

    def test_strong_metrics_password_not_flagged(self):
        fake = _make_fake_settings(METRICS_PASSWORD="xK9mP2qL7nR4wZ8v")  # pragma: allowlist secret
        with (
            patch("app.services.secrets_validation_service.settings", fake),
            patch.dict("os.environ", {
                "DATABASE_URL": "postgresql://u:X9kQ@db/prod",  # pragma: allowlist secret
                "DATABASE_URL_TEST": "postgresql://u:X9kQ@db/test",  # pragma: allowlist secret
            }),
        ):
            result = SecretsValidationService.validate_production_secrets()
        metrics_errors = [e for e in result["errors"] if "METRICS_PASSWORD" in e]
        assert metrics_errors == []


@pytest.mark.unit
class TestSecretsValidationServiceMetricsUsername:
    """validate_production_secrets must catch default metrics usernames."""

    def test_default_admin_username_flagged(self):
        fake = _make_fake_settings(METRICS_USERNAME="admin")
        with patch("app.services.secrets_validation_service.settings", fake):
            result = SecretsValidationService.validate_production_secrets()
        assert any("METRICS_USERNAME" in e for e in result["errors"])

    def test_metrics_username_flagged(self):
        fake = _make_fake_settings(METRICS_USERNAME="metrics")
        with patch("app.services.secrets_validation_service.settings", fake):
            result = SecretsValidationService.validate_production_secrets()
        assert any("METRICS_USERNAME" in e for e in result["errors"])

    def test_custom_username_not_flagged(self):
        fake = _make_fake_settings(METRICS_USERNAME="metrics_reader")
        with (
            patch("app.services.secrets_validation_service.settings", fake),
            patch.dict("os.environ", {
                "DATABASE_URL": "postgresql://u:X9kQ@db/prod",  # pragma: allowlist secret
                "DATABASE_URL_TEST": "postgresql://u:X9kQ@db/test",  # pragma: allowlist secret
            }),
        ):
            result = SecretsValidationService.validate_production_secrets()
        username_errors = [e for e in result["errors"] if "METRICS_USERNAME" in e]
        assert username_errors == []


@pytest.mark.unit
class TestMetricsChecklist:
    """generate_security_checklist must include both metrics credential entries."""

    def test_checklist_strong_credentials_pass(self):
        fake = _make_fake_settings(
            METRICS_PASSWORD="xK9mP2qL7nR4wZ8v",  # pragma: allowlist secret
            METRICS_USERNAME="metrics_reader",
        )
        with patch("app.services.secrets_validation_service.settings", fake):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["metrics_password_changed"] is True
        assert checklist["metrics_username_changed"] is True

    def test_checklist_weak_password_fails(self):
        fake = _make_fake_settings(METRICS_PASSWORD="metrics_admin")  # pragma: allowlist secret
        with patch("app.services.secrets_validation_service.settings", fake):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["metrics_password_changed"] is False

    def test_checklist_short_password_fails(self):
        fake = _make_fake_settings(METRICS_PASSWORD="tooshort")
        with patch("app.services.secrets_validation_service.settings", fake):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["metrics_password_changed"] is False

    def test_checklist_default_username_fails(self):
        fake = _make_fake_settings(METRICS_USERNAME="admin")
        with patch("app.services.secrets_validation_service.settings", fake):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["metrics_username_changed"] is False
