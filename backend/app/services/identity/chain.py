"""IdentityProviderChain — tries each provider in priority order."""

import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.identity.base import AuthenticatedIdentity, IdentityProvider
from app.services.identity.builtin import BuiltinIdentityProvider
from app.services.identity.oidc import OIDCIdentityProvider, OIDCProviderConfig

logger = logging.getLogger(__name__)

# Module-level singleton (built lazily on first request)
_chain: Optional["IdentityProviderChain"] = None


class IdentityProviderChain:
    """Ordered list of identity providers.

    When a request arrives, each provider's ``can_handle()`` is checked in
    order. The first provider that claims the token (by JWT ``iss`` / ``alg``)
    validates it. If validation fails, the chain raises 401.

    This means you can run multiple providers simultaneously — e.g.
    ``cognito,builtin`` will accept both Cognito-issued RS256 tokens and the
    app's own HS256 tokens without any code changes.
    """

    def __init__(self, providers: list[IdentityProvider]) -> None:
        self._providers = providers

    async def authenticate(
        self, token: str, db: AsyncSession
    ) -> AuthenticatedIdentity:
        """Validate token and return the authenticated identity.

        Raises:
            HTTPException(401): if no provider claims the token, or if the
                claiming provider rejects it.
        """
        for provider in self._providers:
            if provider.can_handle(token):
                identity = await provider.validate_token(token, db)
                if identity is not None:
                    return identity
                # Provider claimed the token but rejected it (expired, bad sig, etc.)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def build_chain() -> IdentityProviderChain:
    """Construct the provider chain from application settings."""
    providers: list[IdentityProvider] = []

    for name in settings.IDENTITY_PROVIDER_CHAIN:
        name = name.strip().lower()

        if name == "builtin":
            providers.append(BuiltinIdentityProvider())
            logger.info("Identity chain: added builtin provider")

        elif name == "cognito":
            if not settings.IDP_COGNITO_ISSUER or not settings.IDP_COGNITO_CLIENT_ID:
                logger.warning(
                    "Identity chain: 'cognito' requested but IDP_COGNITO_ISSUER / "
                    "IDP_COGNITO_CLIENT_ID not set — skipping"
                )
                continue
            providers.append(
                OIDCIdentityProvider(
                    OIDCProviderConfig(
                        provider_name="cognito",
                        issuer=settings.IDP_COGNITO_ISSUER,
                        client_id=settings.IDP_COGNITO_CLIENT_ID,
                        admin_group=settings.IDP_COGNITO_ADMIN_GROUP,
                        groups_claim="cognito:groups",
                    )
                )
            )
            logger.info("Identity chain: added Cognito provider iss=%s", settings.IDP_COGNITO_ISSUER)

        elif name == "keycloak":
            if not settings.IDP_KEYCLOAK_ISSUER or not settings.IDP_KEYCLOAK_CLIENT_ID:
                logger.warning(
                    "Identity chain: 'keycloak' requested but config not set — skipping"
                )
                continue
            providers.append(
                OIDCIdentityProvider(
                    OIDCProviderConfig(
                        provider_name="keycloak",
                        issuer=settings.IDP_KEYCLOAK_ISSUER,
                        client_id=settings.IDP_KEYCLOAK_CLIENT_ID,
                        admin_group=settings.IDP_KEYCLOAK_ADMIN_GROUP,
                        groups_claim=settings.IDP_KEYCLOAK_GROUPS_CLAIM,
                    )
                )
            )
            logger.info("Identity chain: added Keycloak provider iss=%s", settings.IDP_KEYCLOAK_ISSUER)

        elif name == "okta":
            if not settings.IDP_OKTA_ISSUER or not settings.IDP_OKTA_CLIENT_ID:
                logger.warning(
                    "Identity chain: 'okta' requested but config not set — skipping"
                )
                continue
            providers.append(
                OIDCIdentityProvider(
                    OIDCProviderConfig(
                        provider_name="okta",
                        issuer=settings.IDP_OKTA_ISSUER,
                        client_id=settings.IDP_OKTA_CLIENT_ID,
                        admin_group="",
                        groups_claim=settings.IDP_OKTA_GROUPS_CLAIM,
                    )
                )
            )
            logger.info("Identity chain: added Okta provider iss=%s", settings.IDP_OKTA_ISSUER)

        elif name == "google":
            if not settings.IDP_GOOGLE_CLIENT_ID:
                logger.warning(
                    "Identity chain: 'google' requested but IDP_GOOGLE_CLIENT_ID not set — skipping"
                )
                continue
            providers.append(
                OIDCIdentityProvider(
                    OIDCProviderConfig(
                        provider_name="google",
                        issuer="https://accounts.google.com",
                        client_id=settings.IDP_GOOGLE_CLIENT_ID,
                        admin_group="",
                        groups_claim="",  # Google doesn't expose groups
                        # Google tokens use the client_id as audience
                        extra_audiences=[],
                    )
                )
            )
            logger.info("Identity chain: added Google provider")

        else:
            logger.warning("Identity chain: unknown provider %r — skipping", name)

    if not providers:
        # Safe fallback: always have at least the built-in provider
        logger.warning(
            "Identity chain: no valid providers configured — falling back to builtin"
        )
        providers.append(BuiltinIdentityProvider())

    return IdentityProviderChain(providers)


def get_chain() -> IdentityProviderChain:
    """Return the singleton chain, building it on first call."""
    global _chain
    if _chain is None:
        _chain = build_chain()
    return _chain


def reset_chain() -> None:
    """Reset the singleton chain (used in tests to re-read config)."""
    global _chain
    _chain = None
