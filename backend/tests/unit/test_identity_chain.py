"""Unit tests for the identity provider chain."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.services.identity.base import AuthenticatedIdentity, IdentityProvider
from app.services.identity.builtin import BuiltinIdentityProvider
from app.services.identity.chain import (
    IdentityProviderChain,
    build_chain,
    get_chain,
    reset_chain,
)


def _make_identity(user_id=None):
    uid = user_id or uuid4()
    return AuthenticatedIdentity(
        user_id=uid,
        provider="builtin",
        subject=str(uid),
        email="test@example.com",
        groups=[],
        raw_claims={"type": "access", "sub": str(uid)},
    )


# ---------------------------------------------------------------------------
# IdentityProviderChain
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIdentityProviderChain:
    """Test the chain orchestrator."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_first_matching_provider_wins(self, mock_db):
        """Chain returns identity from the first provider that can_handle the token."""
        provider_a = Mock(spec=IdentityProvider)
        provider_a.can_handle = Mock(return_value=False)

        uid = uuid4()
        provider_b = Mock(spec=IdentityProvider)
        provider_b.can_handle = Mock(return_value=True)
        provider_b.validate_token = AsyncMock(return_value=_make_identity(uid))

        chain = IdentityProviderChain([provider_a, provider_b])
        identity = await chain.authenticate("token", mock_db)

        assert identity.user_id == uid
        provider_a.validate_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_matching_provider_raises_401(self, mock_db):
        """Chain raises 401 when no provider claims the token."""
        provider = Mock(spec=IdentityProvider)
        provider.can_handle = Mock(return_value=False)

        chain = IdentityProviderChain([provider])
        with pytest.raises(HTTPException) as exc_info:
            await chain.authenticate("token", mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_provider_claims_but_rejects_raises_401(self, mock_db):
        """Chain raises 401 when provider claims the token but validation fails."""
        provider = Mock(spec=IdentityProvider)
        provider.can_handle = Mock(return_value=True)
        provider.validate_token = AsyncMock(return_value=None)

        chain = IdentityProviderChain([provider])
        with pytest.raises(HTTPException) as exc_info:
            await chain.authenticate("token", mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_chain_raises_401(self, mock_db):
        """Chain with no providers raises 401."""
        chain = IdentityProviderChain([])
        with pytest.raises(HTTPException) as exc_info:
            await chain.authenticate("token", mock_db)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# BuiltinIdentityProvider
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuiltinIdentityProvider:
    """Test the app-native HS256 provider."""

    @pytest.fixture
    def provider(self):
        return BuiltinIdentityProvider()

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    def test_can_handle_hs256_token(self, provider):
        """Should return True for HS256 tokens (app's own JWTs)."""
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(uuid4()), "email": "test@example.com"})
        assert provider.can_handle(token) is True

    def test_cannot_handle_garbage(self, provider):
        """Should return False for malformed tokens."""
        assert provider.can_handle("not-a-jwt") is False
        assert provider.can_handle("") is False

    @pytest.mark.asyncio
    async def test_validates_access_token(self, provider, mock_db):
        """Should return identity for a valid access token."""
        from app.core.security import create_access_token
        user_id = uuid4()
        token = create_access_token({"sub": str(user_id), "email": "test@example.com", "type": "access"})

        identity = await provider.validate_token(token, mock_db)
        assert identity is not None
        assert identity.user_id == user_id
        assert identity.provider == "builtin"

    @pytest.mark.asyncio
    async def test_rejects_refresh_token(self, provider, mock_db):
        """Should return None for a refresh token (wrong type)."""
        # create_refresh_token returns (raw_token, jti, expires_at)
        from app.core.security import create_refresh_token
        raw_token, _jti, _exp = create_refresh_token(user_id=str(uuid4()))

        identity = await provider.validate_token(raw_token, mock_db)
        assert identity is None

    @pytest.mark.asyncio
    async def test_rejects_invalid_token(self, provider, mock_db):
        """Should return None for a completely invalid token."""
        identity = await provider.validate_token("garbage.token.here", mock_db)
        assert identity is None


# ---------------------------------------------------------------------------
# build_chain / get_chain / reset_chain
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildChain:
    """Test chain factory and singleton helpers."""

    def setup_method(self):
        reset_chain()

    def teardown_method(self):
        reset_chain()

    def test_default_chain_has_builtin(self):
        """build_chain() with default config should include builtin provider."""
        chain = build_chain()
        assert any(isinstance(p, BuiltinIdentityProvider) for p in chain._providers)

    def test_get_chain_returns_same_instance(self):
        """get_chain() should return the same singleton object each time."""
        chain1 = get_chain()
        chain2 = get_chain()
        assert chain1 is chain2

    def test_reset_chain_clears_singleton(self):
        """reset_chain() should force a new build on the next get_chain() call."""
        chain1 = get_chain()
        reset_chain()
        chain2 = get_chain()
        assert chain1 is not chain2

    def test_unknown_provider_name_is_skipped(self):
        """Unknown provider names should be gracefully ignored."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.IDENTITY_PROVIDER_CHAIN = ["nonexistent_provider", "builtin"]
            # Provide stub values for all IDP_ attrs accessed in build_chain
            mock_settings.IDP_COGNITO_ISSUER = None
            mock_settings.IDP_COGNITO_CLIENT_ID = None
            mock_settings.IDP_COGNITO_ADMIN_GROUP = "admins"
            mock_settings.IDP_KEYCLOAK_ISSUER = None
            mock_settings.IDP_KEYCLOAK_CLIENT_ID = None
            mock_settings.IDP_KEYCLOAK_ADMIN_GROUP = "admins"
            mock_settings.IDP_KEYCLOAK_GROUPS_CLAIM = "groups"
            mock_settings.IDP_OKTA_ISSUER = None
            mock_settings.IDP_OKTA_CLIENT_ID = None
            mock_settings.IDP_OKTA_GROUPS_CLAIM = "groups"
            mock_settings.IDP_GOOGLE_CLIENT_ID = None
            chain = build_chain()
        # Should still have builtin
        assert any(isinstance(p, BuiltinIdentityProvider) for p in chain._providers)

    def test_empty_provider_list_falls_back_to_builtin(self):
        """If all providers are invalid, builtin fallback is added automatically."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.IDENTITY_PROVIDER_CHAIN = []
            mock_settings.IDP_COGNITO_ISSUER = None
            mock_settings.IDP_COGNITO_CLIENT_ID = None
            mock_settings.IDP_COGNITO_ADMIN_GROUP = "admins"
            mock_settings.IDP_KEYCLOAK_ISSUER = None
            mock_settings.IDP_KEYCLOAK_CLIENT_ID = None
            mock_settings.IDP_KEYCLOAK_ADMIN_GROUP = "admins"
            mock_settings.IDP_KEYCLOAK_GROUPS_CLAIM = "groups"
            mock_settings.IDP_OKTA_ISSUER = None
            mock_settings.IDP_OKTA_CLIENT_ID = None
            mock_settings.IDP_OKTA_GROUPS_CLAIM = "groups"
            mock_settings.IDP_GOOGLE_CLIENT_ID = None
            chain = build_chain()
        assert len(chain._providers) >= 1
        assert any(isinstance(p, BuiltinIdentityProvider) for p in chain._providers)
