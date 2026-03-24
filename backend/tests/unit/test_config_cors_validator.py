"""Tests for CORS_ORIGINS validator in Settings."""

import os
from unittest.mock import patch

import pytest

from app.config import Settings


@pytest.mark.unit
class TestValidateCorsOrigins:
    """Test the validate_cors_origins classmethod on Settings."""

    def test_accepts_normal_origins_in_production(self):
        """Production should accept non-localhost origins."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            result = Settings.validate_cors_origins(
                ["https://app.nestegg.com", "https://api.nestegg.com"]
            )
        assert result == ["https://app.nestegg.com", "https://api.nestegg.com"]

    def test_rejects_localhost_origins_in_production(self):
        """Production should reject origins containing 'localhost'."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(ValueError, match="localhost"):
                Settings.validate_cors_origins(["http://localhost:3000"])

    def test_rejects_127_0_0_1_origins_in_production(self):
        """Production should reject origins containing '127.0.0.1'."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(ValueError, match="localhost"):
                Settings.validate_cors_origins(["http://127.0.0.1:3000"])

    def test_allows_localhost_origins_in_development(self):
        """Development should allow localhost origins."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            result = Settings.validate_cors_origins(
                ["http://localhost:3000", "http://localhost:5173"]
            )
        assert result == ["http://localhost:3000", "http://localhost:5173"]

    def test_rejects_localhost_origins_in_staging(self):
        """Staging should also reject localhost origins (same as production)."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            with pytest.raises(ValueError, match="localhost"):
                Settings.validate_cors_origins(["http://localhost:3000"])

    def test_mixed_origins_with_localhost_in_production(self):
        """Production should reject when any origin is localhost, even if others are valid."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(ValueError, match="localhost"):
                Settings.validate_cors_origins(["https://app.nestegg.com", "http://localhost:3000"])

    def test_mixed_origins_with_127_in_production(self):
        """Production should reject when any origin is 127.0.0.1, even if others are valid."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(ValueError, match="localhost"):
                Settings.validate_cors_origins(["https://app.nestegg.com", "http://127.0.0.1:5173"])

    def test_empty_origins_accepted_in_production(self):
        """Production should accept an empty list of origins."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            result = Settings.validate_cors_origins([])
        assert result == []

    def test_defaults_to_development_when_env_unset(self):
        """When ENVIRONMENT is not set, should default to development (allow localhost)."""
        env = os.environ.copy()
        env.pop("ENVIRONMENT", None)
        with patch.dict(os.environ, env, clear=True):
            result = Settings.validate_cors_origins(["http://localhost:3000"])
        assert result == ["http://localhost:3000"]

    # --- Wildcard rejection tests ---

    def test_rejects_wildcard_in_production(self):
        """Production must reject CORS_ORIGINS=['*'] — allows any site to make requests."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(ValueError, match=r"\*"):
                Settings.validate_cors_origins(["*"])

    def test_rejects_wildcard_in_staging(self):
        """Staging should also reject wildcard — staging exploits == production exploits."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            with pytest.raises(ValueError, match=r"\*"):
                Settings.validate_cors_origins(["*"])

    def test_rejects_wildcard_mixed_with_valid_origins_in_production(self):
        """Wildcard in a list with otherwise-valid origins must still be rejected."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(ValueError, match=r"\*"):
                Settings.validate_cors_origins(["https://app.nestegg.com", "*"])

    def test_allows_wildcard_in_development(self):
        """Development may use wildcard for convenience (no production risk)."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            result = Settings.validate_cors_origins(["*"])
        assert result == ["*"]

    def test_allows_wildcard_in_test(self):
        """Test environment may use wildcard."""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = Settings.validate_cors_origins(["*"])
        assert result == ["*"]
