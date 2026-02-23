"""Unit tests for OIDCIdentityProvider."""

import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

from app.services.identity.oidc import OIDCIdentityProvider, OIDCProviderConfig


def _make_config(**kwargs):
    defaults = dict(
        provider_name="cognito",
        issuer="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TEST",
        client_id="test_client_id",
        admin_group="nest-egg-admins",
        groups_claim="cognito:groups",
    )
    defaults.update(kwargs)
    return OIDCProviderConfig(**defaults)


@pytest.mark.unit
class TestOIDCProviderCanHandle:
    """Tests for can_handle() issuer matching."""

    def test_matching_issuer_returns_true(self):
        """can_handle returns True when token's iss matches provider issuer."""
        config = _make_config()
        provider = OIDCIdentityProvider(config)

        # Build a fake JWT with the right issuer (unverified decode only)
        import base64
        header = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').rstrip(b"=").decode()
        payload_data = json.dumps({"iss": config.issuer, "sub": "user123"}).encode()
        payload = base64.urlsafe_b64encode(payload_data).rstrip(b"=").decode()
        fake_token = f"{header}.{payload}.fakesig"

        assert provider.can_handle(fake_token) is True

    def test_wrong_issuer_returns_false(self):
        """can_handle returns False when iss does not match."""
        config = _make_config()
        provider = OIDCIdentityProvider(config)

        import base64
        header = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').rstrip(b"=").decode()
        payload_data = json.dumps({"iss": "https://other.issuer.com", "sub": "user123"}).encode()
        payload = base64.urlsafe_b64encode(payload_data).rstrip(b"=").decode()
        fake_token = f"{header}.{payload}.fakesig"

        assert provider.can_handle(fake_token) is False

    def test_garbage_token_returns_false(self):
        """can_handle returns False for malformed tokens."""
        provider = OIDCIdentityProvider(_make_config())
        assert provider.can_handle("not.a.jwt") is False
        assert provider.can_handle("") is False


@pytest.mark.unit
class TestOIDCProviderValidateToken:
    """Tests for validate_token() — mocks JWKS fetch and jwt.decode."""

    @pytest.fixture
    def provider(self):
        return OIDCIdentityProvider(_make_config())

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_valid_token_returns_identity(self, provider, mock_db):
        """Should return AuthenticatedIdentity for a valid OIDC token."""
        user_id_str = str(uuid4())
        claims = {
            "sub": user_id_str,
            "email": "alice@example.com",
            "aud": "test_client_id",
            "iss": provider.config.issuer,
            "cognito:groups": [],
            "exp": int(time.time()) + 3600,
        }

        mock_identity_row = Mock()
        mock_identity_row.user_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_identity_row)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(provider, "_get_jwks", new=AsyncMock(return_value={"keys": []})):
            with patch("app.services.identity.oidc.jose_jwt") as mock_jwt:
                mock_jwt.decode = Mock(return_value=claims)
                mock_jwt.get_unverified_header = Mock(return_value={"alg": "RS256", "kid": "key1"})

                identity = await provider.validate_token("fake.oidc.token", mock_db)

        assert identity is not None
        assert identity.email == "alice@example.com"
        assert identity.provider == "cognito"

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_none(self, provider, mock_db):
        """Should return None when JWT verification fails."""
        from jose import JWTError

        with patch.object(provider, "_get_jwks", new=AsyncMock(return_value={"keys": []})):
            with patch("app.services.identity.oidc.jose_jwt") as mock_jwt:
                mock_jwt.get_unverified_header = Mock(return_value={"alg": "RS256", "kid": "key1"})
                mock_jwt.decode = Mock(side_effect=JWTError("bad signature"))

                identity = await provider.validate_token("bad.oidc.token", mock_db)

        assert identity is None

    @pytest.mark.asyncio
    async def test_jwks_fetch_failure_returns_none(self, provider, mock_db):
        """Should return None when JWKS cannot be fetched."""
        with patch.object(provider, "_get_jwks", new=AsyncMock(side_effect=Exception("network error"))):
            identity = await provider.validate_token("any.token.here", mock_db)

        assert identity is None


@pytest.mark.unit
class TestOIDCProviderConfig:
    """Tests for OIDCProviderConfig validation."""

    def test_basic_config_creation(self):
        config = _make_config()
        assert config.provider_name == "cognito"
        assert config.issuer.startswith("https://")

    def test_google_config_with_empty_groups_claim(self):
        config = _make_config(
            provider_name="google",
            issuer="https://accounts.google.com",
            client_id="google_client_id",
            groups_claim="",  # Google has no groups
            admin_group="",
        )
        assert config.groups_claim == ""
