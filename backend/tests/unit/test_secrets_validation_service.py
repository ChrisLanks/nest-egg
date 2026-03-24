"""Unit tests for SecretsValidationService."""

from unittest.mock import patch

import pytest

from app.services.secrets_validation_service import SecretsValidationService

# ── _is_default_or_weak ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestIsDefaultOrWeak:
    """Test weak/default secret detection."""

    def test_weak_password_pattern(self):
        assert SecretsValidationService._is_default_or_weak("changeme123") is True

    def test_weak_with_password(self):
        assert SecretsValidationService._is_default_or_weak("mypassword") is True

    def test_weak_with_secret(self):
        assert SecretsValidationService._is_default_or_weak("mysecretkey") is True

    def test_weak_with_default(self):
        assert SecretsValidationService._is_default_or_weak("default-key-here") is True

    def test_weak_with_test(self):
        assert SecretsValidationService._is_default_or_weak("testvalue") is True

    def test_weak_with_admin(self):
        assert SecretsValidationService._is_default_or_weak("admin_token") is True

    def test_weak_123456(self):
        assert SecretsValidationService._is_default_or_weak("key_123456_end") is True

    def test_weak_qwerty(self):
        assert SecretsValidationService._is_default_or_weak("qwerty_long_enough") is True

    def test_weak_your_secret_key(self):
        assert SecretsValidationService._is_default_or_weak("your-secret-key-here") is True

    def test_strong_random_string(self):
        assert (
            SecretsValidationService._is_default_or_weak(
                "k8X9mZp2qR7wN4vB6cD1fG3hJ5"  # pragma: allowlist secret
            )
            is False
        )

    def test_repeated_characters(self):
        assert SecretsValidationService._is_default_or_weak("aaaaabcdef") is True

    def test_sequential_pattern(self):
        # 3+ sequential groups: 012012012
        assert SecretsValidationService._is_default_or_weak("012012012") is True

    def test_no_match_returns_false(self):
        assert SecretsValidationService._is_default_or_weak("Xk29$mNp@rQ7wZ") is False


# ── _extract_db_password ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestExtractDbPassword:
    """Test database password extraction from URL."""

    def test_standard_url(self):
        url = "postgresql://user:my_secret_pass@localhost:5432/mydb"  # pragma: allowlist secret
        assert SecretsValidationService._extract_db_password(url) == "my_secret_pass"

    def test_empty_url(self):
        assert SecretsValidationService._extract_db_password("") is None

    def test_none_url(self):
        assert SecretsValidationService._extract_db_password(None) is None

    def test_url_without_password(self):
        url = "postgresql://localhost:5432/mydb"
        assert SecretsValidationService._extract_db_password(url) is None

    def test_complex_password(self):
        url = "postgresql://admin:S3cur3L0ngPwd!#@db.example.com:5432/prod"
        result = SecretsValidationService._extract_db_password(url)
        assert result == "S3cur3L0ngPwd!#"


# ── validate_api_key_format ──────────────────────────────────────────────────


@pytest.mark.unit
class TestValidateApiKeyFormat:
    """Test API key format validation."""

    def test_empty_key_invalid(self):
        assert SecretsValidationService.validate_api_key_format("", "plaid") is False

    def test_plaid_client_valid(self):
        key = "a" * 24
        assert SecretsValidationService.validate_api_key_format(key, "plaid_client") is True

    def test_plaid_client_too_short(self):
        key = "a" * 23
        assert SecretsValidationService.validate_api_key_format(key, "plaid_client") is False

    def test_plaid_client_non_alnum(self):
        key = "a" * 23 + "!"
        assert SecretsValidationService.validate_api_key_format(key, "plaid_client") is False

    def test_plaid_secret_valid(self):
        key = "a" * 30
        assert SecretsValidationService.validate_api_key_format(key, "plaid_secret") is True

    def test_plaid_secret_too_short(self):
        key = "a" * 29
        assert SecretsValidationService.validate_api_key_format(key, "plaid_secret") is False

    def test_generic_provider_valid(self):
        key = "a" * 20
        assert SecretsValidationService.validate_api_key_format(key, "stripe") is True

    def test_generic_provider_too_short(self):
        key = "a" * 19
        assert SecretsValidationService.validate_api_key_format(key, "stripe") is False


# ── validate_production_secrets ──────────────────────────────────────────────


@pytest.mark.unit
class TestValidateProductionSecrets:
    """Test production secrets validation."""

    def _make_settings(self, **overrides):
        """Create a mock settings object with production defaults."""

        class FakeSettings:
            pass

        s = FakeSettings()
        s.DEBUG = overrides.get("DEBUG", False)
        s.SECRET_KEY = overrides.get(
            "SECRET_KEY",
            "k8X9mZp2qR7wN4vB6cD1fG3hJ5kL0mNx",  # pragma: allowlist secret
        )
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
        s.METRICS_PASSWORD = overrides.get("METRICS_PASSWORD", "strong_metrics_pw_2024")
        s.METRICS_USERNAME = overrides.get("METRICS_USERNAME", "metrics_reader")
        s.REDIS_URL = overrides.get(
            "REDIS_URL", "redis://:Xk29mNpRq7wZ8vL4n@redis:6379/0"  # pragma: allowlist secret
        )
        s.SMTP_HOST = overrides.get("SMTP_HOST", None)
        s.SMTP_PASSWORD = overrides.get("SMTP_PASSWORD", None)
        return s

    def test_debug_mode_skips_validation(self):
        with patch("app.services.secrets_validation_service.settings") as mock_settings:
            mock_settings.DEBUG = True
            result = SecretsValidationService.validate_production_secrets()
        assert result["errors"] == []
        assert len(result["warnings"]) == 1

    def test_short_secret_key_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(SECRET_KEY="short"),  # pragma: allowlist secret
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("SECRET_KEY" in e for e in result["errors"])

    def test_weak_secret_key_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(SECRET_KEY="changeme" + "x" * 30),  # pragma: allowlist secret
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("weak" in e.lower() or "default" in e.lower() for e in result["errors"])

    def test_missing_database_url_error(self):
        with patch(
            "app.services.secrets_validation_service.settings", self._make_settings(DATABASE_URL="")
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("DATABASE_URL" in e for e in result["errors"])

    def test_localhost_database_warning(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                DATABASE_URL="postgresql://u:str0ng@localhost:5432/db"  # pragma: allowlist secret
            ),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("localhost" in w for w in result["warnings"])

    def test_short_db_password_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                DATABASE_URL="postgresql://user:short@db.com:5432/db"  # pragma: allowlist secret
            ),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("password" in e.lower() and "short" in e.lower() for e in result["errors"])

    def test_weak_db_password_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                DATABASE_URL="postgresql://u:changeme1234@db:5432/db"  # pragma: allowlist secret
            ),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any(
            "password" in e.lower() and ("weak" in e.lower() or "default" in e.lower())
            for e in result["errors"]
        )

    def test_missing_encryption_key_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(MASTER_ENCRYPTION_KEY=""),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("MASTER_ENCRYPTION_KEY" in e for e in result["errors"])

    def test_short_encryption_key_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(MASTER_ENCRYPTION_KEY="short"),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("MASTER_ENCRYPTION_KEY" in e for e in result["errors"])

    def test_wildcard_cors_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(CORS_ORIGINS=["*"]),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("CORS_ORIGINS" in e for e in result["errors"])

    def test_empty_cors_error(self):
        with patch(
            "app.services.secrets_validation_service.settings", self._make_settings(CORS_ORIGINS=[])
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("CORS_ORIGINS" in e for e in result["errors"])

    def test_localhost_cors_warning(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(CORS_ORIGINS=["http://localhost:3000"]),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("localhost" in w for w in result["warnings"])

    def test_wildcard_allowed_hosts_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(ALLOWED_HOSTS=["*"]),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("ALLOWED_HOSTS" in e for e in result["errors"])

    def test_default_metrics_password_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(METRICS_PASSWORD="metrics_admin"),  # pragma: allowlist secret
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("METRICS_PASSWORD" in e for e in result["errors"])

    def test_missing_plaid_warnings(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(PLAID_CLIENT_ID="", PLAID_SECRET="", PLAID_WEBHOOK_SECRET=""),
        ):
            result = SecretsValidationService.validate_production_secrets()
        plaid_warnings = [w for w in result["warnings"] if "PLAID" in w]
        assert len(plaid_warnings) == 3

    def test_same_db_url_and_test_url_error(self):
        with (
            patch("app.services.secrets_validation_service.settings", self._make_settings()),
            patch.dict(
                "os.environ",
                {
                    "DATABASE_URL": "postgresql://u:p@h/db",  # pragma: allowlist secret
                    "DATABASE_URL_TEST": "postgresql://u:p@h/db",  # pragma: allowlist secret
                },
            ),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("DATABASE_URL_TEST" in e for e in result["errors"])

    def test_all_valid_no_errors(self):
        with (
            patch("app.services.secrets_validation_service.settings", self._make_settings()),
            patch.dict(
                "os.environ",
                {
                    "DATABASE_URL": "postgresql://user:pass@host/db",  # pragma: allowlist secret
                    "DATABASE_URL_TEST": "postgresql://u:p@h/testdb",  # pragma: allowlist secret
                },
            ),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert result["errors"] == []


# ── generate_security_checklist ──────────────────────────────────────────────


@pytest.mark.unit
class TestGenerateSecurityChecklist:
    """Test security checklist generation."""

    def _make_settings(self, **overrides):
        class FakeSettings:
            pass

        s = FakeSettings()
        s.DEBUG = overrides.get("DEBUG", False)
        s.SECRET_KEY = overrides.get(
            "SECRET_KEY",
            "k8X9mZp2qR7wN4vB6cD1fG3hJ5kL0mNx",  # pragma: allowlist secret
        )
        s.DATABASE_URL = overrides.get(
            "DATABASE_URL",
            "postgresql://u:X9kQ!mZ2vL8nR4wY@db:5432/prod",  # pragma: allowlist secret
        )
        s.MASTER_ENCRYPTION_KEY = overrides.get("MASTER_ENCRYPTION_KEY", "b" * 32)
        s.CORS_ORIGINS = overrides.get("CORS_ORIGINS", ["https://app.example.com"])
        s.ALLOWED_HOSTS = overrides.get("ALLOWED_HOSTS", ["app.example.com"])
        s.PLAID_CLIENT_ID = overrides.get("PLAID_CLIENT_ID", "plaid_client_id_val")
        s.PLAID_SECRET = overrides.get("PLAID_SECRET", "plaid_secret_val")
        s.PLAID_WEBHOOK_SECRET = overrides.get("PLAID_WEBHOOK_SECRET", "webhook_val")
        s.METRICS_PASSWORD = overrides.get("METRICS_PASSWORD", "strong_metrics_pw_2024")
        s.METRICS_USERNAME = overrides.get("METRICS_USERNAME", "metrics_reader")
        s.REDIS_URL = overrides.get(
            "REDIS_URL", "redis://:Xk29mNpRq7wZ8vL4n@redis:6379/0"  # pragma: allowlist secret
        )
        s.SMTP_HOST = overrides.get("SMTP_HOST", None)
        s.SMTP_PASSWORD = overrides.get("SMTP_PASSWORD", None)
        return s

    def test_all_checks_pass(self):
        with patch("app.services.secrets_validation_service.settings", self._make_settings()):
            checklist = SecretsValidationService.generate_security_checklist()

        assert checklist["debug_disabled"] is True
        assert checklist["secret_key_strong"] is True
        assert checklist["database_configured"] is True
        assert checklist["database_not_localhost"] is True
        assert checklist["encryption_key_set"] is True
        assert checklist["cors_configured"] is True
        assert checklist["allowed_hosts_configured"] is True
        assert checklist["plaid_configured"] is True
        assert checklist["plaid_webhook_verified"] is True
        assert checklist["metrics_password_changed"] is True
        assert checklist["metrics_username_changed"] is True
        assert checklist["redis_password_strong"] is True
        assert checklist["smtp_password_strong"] is True  # SMTP not configured — N/A → True

    def test_debug_enabled_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings", self._make_settings(DEBUG=True)
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["debug_disabled"] is False

    def test_weak_secret_key_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                SECRET_KEY="changeme_long_enough_key_12345"  # pragma: allowlist secret
            ),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["secret_key_strong"] is False

    def test_localhost_database_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                DATABASE_URL="postgresql://user:pass@localhost:5432/db"  # pragma: allowlist secret
            ),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["database_not_localhost"] is False

    def test_no_encryption_key_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(MASTER_ENCRYPTION_KEY=""),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["encryption_key_set"] is False

    def test_localhost_cors_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(CORS_ORIGINS=["http://localhost:3000"]),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["cors_configured"] is False

    def test_wildcard_hosts_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(ALLOWED_HOSTS=["*"]),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["allowed_hosts_configured"] is False

    def test_default_metrics_password_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(METRICS_PASSWORD="admin"),  # pragma: allowlist secret
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["metrics_password_changed"] is False

    def test_no_plaid_configured_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(PLAID_CLIENT_ID="", PLAID_SECRET=""),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["plaid_configured"] is False

    def test_no_plaid_webhook_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(PLAID_WEBHOOK_SECRET=""),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["plaid_webhook_verified"] is False

    def test_weak_redis_password_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(REDIS_URL="redis://:changeme@redis:6379/0"),  # pragma: allowlist secret
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["redis_password_strong"] is False

    def test_strong_redis_password_passes(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(REDIS_URL="redis://:Xk29mNpRq7wZ8vL4n@redis:6379/0"),  # pragma: allowlist secret
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["redis_password_strong"] is True

    def test_redis_no_password_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(REDIS_URL="redis://redis:6379/0"),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["redis_password_strong"] is False

    def test_smtp_not_configured_passes(self):
        """SMTP not configured is not a security issue."""
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(SMTP_HOST=None, SMTP_PASSWORD=None),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["smtp_password_strong"] is True

    def test_smtp_configured_with_strong_password_passes(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                SMTP_HOST="smtp.example.com",
                SMTP_PASSWORD="Xk29mNpRq7wZ8vL4n",  # pragma: allowlist secret
            ),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["smtp_password_strong"] is True

    def test_smtp_configured_with_weak_password_fails(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                SMTP_HOST="smtp.example.com",
                SMTP_PASSWORD="password123",  # pragma: allowlist secret
            ),
        ):
            checklist = SecretsValidationService.generate_security_checklist()
        assert checklist["smtp_password_strong"] is False


# ── _extract_redis_password ───────────────────────────────────────────────────


@pytest.mark.unit
class TestExtractRedisPassword:
    """Test Redis password extraction from URL."""

    def test_password_with_empty_user(self):
        url = "redis://:mypassword@redis:6379/0"  # pragma: allowlist secret
        assert SecretsValidationService._extract_redis_password(url) == "mypassword"

    def test_password_with_username(self):
        url = "redis://user:mypassword@redis:6379/0"  # pragma: allowlist secret
        assert SecretsValidationService._extract_redis_password(url) == "mypassword"

    def test_no_auth(self):
        url = "redis://redis:6379/0"
        assert SecretsValidationService._extract_redis_password(url) is None

    def test_empty_url(self):
        assert SecretsValidationService._extract_redis_password("") is None

    def test_none_url(self):
        assert SecretsValidationService._extract_redis_password(None) is None


# ── Redis + SMTP validate_production_secrets ──────────────────────────────────


@pytest.mark.unit
class TestRedisAndSmtpProductionValidation:
    """Test Redis and SMTP credential validation in production secrets check."""

    def _make_settings(self, **overrides):
        class FakeSettings:
            pass

        s = FakeSettings()
        s.DEBUG = False
        s.SECRET_KEY = "k8X9mZp2qR7wN4vB6cD1fG3hJ5kL0mNx"  # pragma: allowlist secret
        s.DATABASE_URL = "postgresql://u:X9kQ!mZ2vL8nR4wY@db:5432/prod"  # pragma: allowlist secret
        s.MASTER_ENCRYPTION_KEY = "a" * 32
        s.CORS_ORIGINS = ["https://app.example.com"]
        s.ALLOWED_HOSTS = ["app.example.com"]
        s.PLAID_CLIENT_ID = "plaid_client_id_val"
        s.PLAID_SECRET = "plaid_secret_val"
        s.PLAID_WEBHOOK_SECRET = "webhook_val"
        s.METRICS_PASSWORD = "strong_metrics_pw_2024"
        s.METRICS_USERNAME = "metrics_reader"
        s.REDIS_URL = overrides.get(
            "REDIS_URL", "redis://:Xk29mNpRq7wZ8vL4n@redis:6379/0"  # pragma: allowlist secret
        )
        s.SMTP_HOST = overrides.get("SMTP_HOST", None)
        s.SMTP_PASSWORD = overrides.get("SMTP_PASSWORD", None)
        return s

    def test_short_redis_password_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(REDIS_URL="redis://:short@redis:6379/0"),  # pragma: allowlist secret
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("REDIS_URL" in e and "short" in e.lower() for e in result["errors"])

    def test_weak_redis_password_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(REDIS_URL="redis://:changeme123456789@redis:6379/0"),  # pragma: allowlist secret
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("REDIS_URL" in e and ("default" in e.lower() or "weak" in e.lower()) for e in result["errors"])

    def test_redis_localhost_warning(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(REDIS_URL="redis://:Xk29mNpRq7wZ8vL4n@localhost:6379/0"),  # pragma: allowlist secret
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("REDIS_URL" in w or "localhost" in w for w in result["warnings"])

    def test_redis_no_password_no_error(self):
        """Redis without auth (network-isolated) is a warning, not an error."""
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(REDIS_URL="redis://redis:6379/0"),
        ):
            result = SecretsValidationService.validate_production_secrets()
        # No REDIS_URL errors expected — no password means no weak-password check fires
        assert not any("REDIS_URL" in e for e in result["errors"])

    def test_smtp_short_password_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(SMTP_HOST="smtp.example.com", SMTP_PASSWORD="short"),  # pragma: allowlist secret
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("SMTP_PASSWORD" in e for e in result["errors"])

    def test_smtp_weak_password_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                SMTP_HOST="smtp.example.com",
                SMTP_PASSWORD="password_long_enough_12345",  # pragma: allowlist secret
            ),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert any("SMTP_PASSWORD" in e for e in result["errors"])

    def test_smtp_not_configured_no_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(SMTP_HOST=None, SMTP_PASSWORD=None),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert not any("SMTP" in e for e in result["errors"])

    def test_smtp_strong_password_no_error(self):
        with patch(
            "app.services.secrets_validation_service.settings",
            self._make_settings(
                SMTP_HOST="smtp.example.com",
                SMTP_PASSWORD="Xk29mNpRq7wZ8vL4n",  # pragma: allowlist secret
            ),
        ):
            result = SecretsValidationService.validate_production_secrets()
        assert not any("SMTP" in e for e in result["errors"])
