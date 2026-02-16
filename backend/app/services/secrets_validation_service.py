"""Secrets validation service for environment and configuration security."""

import os
import re
from typing import List, Dict, Optional
from app.config import settings


class SecretsValidationService:
    """Service for validating secrets and environment configuration."""

    # Minimum lengths for various secret types
    MIN_SECRET_LENGTHS = {
        'jwt': 32,
        'encryption': 32,
        'database_password': 16,
        'api_key': 20,
    }

    @staticmethod
    def validate_production_secrets() -> Dict[str, List[str]]:
        """
        Validate that all required secrets are properly configured for production.

        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []

        # Only enforce in production
        if settings.DEBUG:
            return {"errors": [], "warnings": ["Running in DEBUG mode - secrets not validated"]}

        # Critical: JWT Secret Key
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < SecretsValidationService.MIN_SECRET_LENGTHS['jwt']:
            errors.append(
                f"SECRET_KEY must be at least {SecretsValidationService.MIN_SECRET_LENGTHS['jwt']} characters in production"
            )
        elif SecretsValidationService._is_default_or_weak(settings.SECRET_KEY):
            errors.append("SECRET_KEY appears to be a default or weak value")

        # Critical: Database URL
        if not settings.DATABASE_URL:
            errors.append("DATABASE_URL must be set in production")
        elif "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL:
            warnings.append("DATABASE_URL points to localhost - ensure this is intentional in production")

        # Check database password strength (if extractable from URL)
        db_password = SecretsValidationService._extract_db_password(settings.DATABASE_URL)
        if db_password:
            if len(db_password) < SecretsValidationService.MIN_SECRET_LENGTHS['database_password']:
                errors.append("Database password is too short (minimum 16 characters)")
            if SecretsValidationService._is_default_or_weak(db_password):
                errors.append("Database password appears to be weak or default")

        # Critical: Encryption Key
        if not settings.MASTER_ENCRYPTION_KEY:
            errors.append("MASTER_ENCRYPTION_KEY must be set in production (used for Plaid tokens)")
        elif len(settings.MASTER_ENCRYPTION_KEY) < SecretsValidationService.MIN_SECRET_LENGTHS['encryption']:
            errors.append(
                f"MASTER_ENCRYPTION_KEY must be at least {SecretsValidationService.MIN_SECRET_LENGTHS['encryption']} characters"
            )

        # Important: CORS Origins
        if not settings.CORS_ORIGINS or settings.CORS_ORIGINS == ["*"]:
            errors.append("CORS_ORIGINS must be set to specific domains in production")
        elif any("localhost" in origin for origin in settings.CORS_ORIGINS):
            warnings.append("CORS_ORIGINS includes localhost - remove for production")

        # Important: Allowed Hosts
        if not settings.ALLOWED_HOSTS or settings.ALLOWED_HOSTS == ["*"]:
            errors.append("ALLOWED_HOSTS must be set to specific domains in production")

        # Optional but recommended: Plaid secrets
        if not settings.PLAID_CLIENT_ID:
            warnings.append("PLAID_CLIENT_ID not set - Plaid integration will not work")
        if not settings.PLAID_SECRET:
            warnings.append("PLAID_SECRET not set - Plaid integration will not work")
        if not settings.PLAID_WEBHOOK_SECRET:
            warnings.append("PLAID_WEBHOOK_SECRET not set - webhook verification disabled")

        # Check for environment-specific issues
        if os.getenv("DATABASE_URL") == os.getenv("DATABASE_URL_TEST"):
            errors.append("DATABASE_URL and DATABASE_URL_TEST are the same - risk of data loss")

        return {"errors": errors, "warnings": warnings}

    @staticmethod
    def _is_default_or_weak(secret: str) -> bool:
        """
        Check if a secret appears to be default or weak.

        Args:
            secret: Secret to check

        Returns:
            True if secret appears weak
        """
        secret_lower = secret.lower()

        # Check for common weak patterns
        weak_patterns = [
            'changeme', 'password', 'secret', 'default', 'test', 'admin',
            '123456', 'qwerty', 'abc123', 'letmein', 'welcome',
            'supersecret', 'mysecret', 'secretkey', 'your-secret-key',
        ]

        for pattern in weak_patterns:
            if pattern in secret_lower:
                return True

        # Check for sequential characters
        if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def){3,}', secret_lower):
            return True

        # Check for repeated characters
        if re.search(r'(.)\1{4,}', secret):
            return True

        return False

    @staticmethod
    def _extract_db_password(database_url: str) -> Optional[str]:
        """
        Extract password from database URL.

        Args:
            database_url: PostgreSQL connection string

        Returns:
            Password if extractable, None otherwise
        """
        if not database_url:
            return None

        # Match password in postgresql://user:password@host:port/database
        match = re.search(r'://[^:]+:([^@]+)@', database_url)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def validate_api_key_format(api_key: str, provider: str) -> bool:
        """
        Validate API key format for known providers.

        Args:
            api_key: API key to validate
            provider: Provider name (plaid, stripe, etc.)

        Returns:
            True if format appears valid
        """
        if not api_key:
            return False

        provider_lower = provider.lower()

        # Plaid keys
        if 'plaid' in provider_lower:
            # Plaid client IDs start with hex string
            # Plaid secrets are longer
            if 'client' in provider_lower:
                return len(api_key) >= 24 and api_key.isalnum()
            else:
                return len(api_key) >= 30 and api_key.isalnum()

        # Generic validation
        return len(api_key) >= SecretsValidationService.MIN_SECRET_LENGTHS['api_key']

    @staticmethod
    def generate_security_checklist() -> Dict[str, bool]:
        """
        Generate a checklist of security configurations.

        Returns:
            Dictionary of security checks and their pass/fail status
        """
        checklist = {}

        # Environment
        checklist['debug_disabled'] = not settings.DEBUG
        checklist['secret_key_strong'] = (
            bool(settings.SECRET_KEY) and
            len(settings.SECRET_KEY) >= SecretsValidationService.MIN_SECRET_LENGTHS['jwt'] and
            not SecretsValidationService._is_default_or_weak(settings.SECRET_KEY)
        )

        # Database
        checklist['database_configured'] = bool(settings.DATABASE_URL)
        checklist['database_not_localhost'] = (
            bool(settings.DATABASE_URL) and
            "localhost" not in settings.DATABASE_URL and
            "127.0.0.1" not in settings.DATABASE_URL
        )

        # Encryption
        checklist['encryption_key_set'] = (
            bool(settings.MASTER_ENCRYPTION_KEY) and
            len(settings.MASTER_ENCRYPTION_KEY) >= SecretsValidationService.MIN_SECRET_LENGTHS['encryption']
        )

        # Network security
        checklist['cors_configured'] = (
            bool(settings.CORS_ORIGINS) and
            settings.CORS_ORIGINS != ["*"] and
            not any("localhost" in origin for origin in settings.CORS_ORIGINS)
        )
        checklist['allowed_hosts_configured'] = (
            bool(settings.ALLOWED_HOSTS) and
            settings.ALLOWED_HOSTS != ["*"]
        )

        # External services
        checklist['plaid_configured'] = bool(settings.PLAID_CLIENT_ID and settings.PLAID_SECRET)
        checklist['plaid_webhook_verified'] = bool(settings.PLAID_WEBHOOK_SECRET)

        return checklist


# Create singleton instance
secrets_validation_service = SecretsValidationService()
