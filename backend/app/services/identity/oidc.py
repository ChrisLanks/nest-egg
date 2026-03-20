"""Generic OIDC identity provider — supports Cognito, Keycloak, Okta, Google."""

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
import jwt as jose_jwt
from jwt import PyJWKSet
from jwt.exceptions import InvalidTokenError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.models.identity import UserIdentity
from app.models.transaction import Category
from app.models.user import ConsentType, Organization, User, UserConsent
from app.services.identity.base import AuthenticatedIdentity, IdentityProvider
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# JWKS cache TTL
_JWKS_TTL = timedelta(hours=1)


@dataclass
class OIDCProviderConfig:
    """Configuration for one OIDC provider instance."""

    provider_name: str  # 'cognito', 'keycloak', 'okta', 'google'
    issuer: str  # Must match the JWT iss claim exactly
    client_id: str  # Used for audience validation

    # Group claim config (IdP-specific)
    admin_group: str = ""  # Group name that maps to is_org_admin=True
    # JWT claim containing group memberships.
    # Cognito: "cognito:groups"; Google: "" (no groups)
    groups_claim: str = "groups"

    # When True, auto-create a User + UserIdentity row on first external login
    auto_provision: bool = True

    # Extra audience values accepted in addition to client_id
    extra_audiences: list = field(default_factory=list)


class OIDCIdentityProvider(IdentityProvider):
    """Validates RS256 OIDC tokens from any standards-compliant provider.

    Supported providers (configured via env vars):
    - AWS Cognito  (``IDP_COGNITO_*``)
    - Keycloak     (``IDP_KEYCLOAK_*``)
    - Okta         (``IDP_OKTA_*``)
    - Google       (``IDP_GOOGLE_CLIENT_ID``)

    JWKS keys are cached for 1 hour and refreshed automatically.
    """

    def __init__(self, config: OIDCProviderConfig) -> None:
        self.config = config
        self.provider_name = config.provider_name
        self._jwks_cache: Optional[dict] = None
        self._jwks_fetched_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # IdentityProvider interface
    # ------------------------------------------------------------------

    def can_handle(self, token: str) -> bool:
        """Return True if the token's iss claim matches our configured issuer."""
        try:
            unverified = jose_jwt.decode(
                token,
                algorithms=["RS256"],
                options={"verify_signature": False, "verify_exp": False},
            )
            return unverified.get("iss") == self.config.issuer
        except Exception:
            return False

    async def validate_token(self, token: str, db: AsyncSession) -> Optional[AuthenticatedIdentity]:
        """Validate RS256 OIDC token and return authenticated identity.

        Returns None only when this provider should not handle the token (wrong
        issuer / unknown kid — let the chain try the next provider). Raises
        HTTPException(401) when this provider owns the token but it is invalid
        (expired, bad signature, bad audience, etc.).
        """
        from fastapi import HTTPException
        from fastapi import status as http_status

        try:
            jwks_data = await self._get_jwks()
        except Exception as exc:
            logger.warning(
                "OIDC JWKS fetch failed for %s: %s — rejecting token",
                self.config.provider_name,
                exc,
            )
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"Identity provider '{self.config.provider_name}' is temporarily unavailable"
                ),
            )

        try:
            jwk_set = PyJWKSet.from_dict(jwks_data)
            header = jose_jwt.get_unverified_header(token)
            kid = header.get("kid")
            signing_key = None
            for jwk in jwk_set.keys:
                if jwk.key_id == kid:
                    signing_key = jwk.key
                    break
            if signing_key is None:
                # Unknown kid — not our token, let the chain try the next provider
                logger.debug("No matching JWK kid=%s for %s", kid, self.config.provider_name)
                return None
            payload = jose_jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=[self.config.client_id] + self.config.extra_audiences,
                issuer=self.config.issuer,
            )
        except JWTError as exc:
            # Known kid but token is invalid (expired, bad sig, wrong audience, etc.)
            # The token belongs to us but is rejected — raise 401 rather than
            # silently returning None (which would let another provider attempt it).
            logger.debug("OIDC token validation failed for %s: %s", self.config.provider_name, exc)
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as exc:
            logger.warning(
                "Unexpected error validating OIDC token for %s: %s",
                self.config.provider_name,
                exc,
            )
            return None

        sub = payload.get("sub")
        email = payload.get("email", "")
        if not sub:
            return None

        groups: list = []
        if self.config.groups_claim:
            raw_groups = payload.get(self.config.groups_claim, [])
            if isinstance(raw_groups, list):
                groups = [str(g) for g in raw_groups]

        # Resolve (or provision) user in app DB
        user_id = await self._resolve_user(db, sub, email, groups)
        if user_id is None:
            return None

        return AuthenticatedIdentity(
            user_id=user_id,
            provider=self.config.provider_name,
            subject=sub,
            email=email,
            groups=groups,
            raw_claims=payload,
        )

    # ------------------------------------------------------------------
    # JWKS helpers
    # ------------------------------------------------------------------

    async def _get_jwks(self) -> dict:
        """Fetch and cache JWKS from the provider's well-known endpoint.

        Uses a 5-second connect + 10-second read timeout. On failure, returns
        the stale cache if available (allows short IdP outages to be transparent).
        Raises on hard failure with no cache available.
        """
        now = datetime.now(tz=timezone.utc)
        if (
            self._jwks_cache is not None
            and self._jwks_fetched_at is not None
            and now - self._jwks_fetched_at < _JWKS_TTL
        ):
            return self._jwks_cache

        jwks_uri = f"{self.config.issuer}/.well-known/jwks.json"
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._jwks_fetched_at = now
                return self._jwks_cache
        except Exception as exc:
            if self._jwks_cache is not None:
                # Serve stale cache rather than breaking all auth during IdP blips
                logger.warning(
                    "JWKS refresh failed for %s (%s) — serving stale cache",
                    self.config.provider_name,
                    exc,
                )
                return self._jwks_cache
            raise

    # ------------------------------------------------------------------
    # User resolution / auto-provisioning
    # ------------------------------------------------------------------

    async def _resolve_user(
        self, db: AsyncSession, sub: str, email: str, groups: list
    ) -> Optional[UUID]:
        """Look up existing UserIdentity row, or auto-provision a new user."""
        result = await db.execute(
            select(UserIdentity).where(
                UserIdentity.provider == self.config.provider_name,
                UserIdentity.provider_subject == sub,
            )
        )
        identity = result.scalar_one_or_none()

        if identity:
            # Refresh group membership + last_seen timestamp
            identity.provider_groups = groups
            identity.last_seen_at = utc_now()
            # Sync admin status if group membership changed
            user_result = await db.execute(select(User).where(User.id == identity.user_id))
            user = user_result.scalar_one_or_none()
            if user and self.config.admin_group:
                user.is_org_admin = self.config.admin_group in groups
            await db.commit()
            return identity.user_id

        # Identity not found
        if not self.config.auto_provision:
            logger.warning(
                "OIDC user not found and auto_provision=False: provider=%s sub=%s",
                self.config.provider_name,
                sub,
            )
            return None

        return await self._provision_user(db, sub, email, groups)

    async def _provision_user(
        self, db: AsyncSession, sub: str, email: str, groups: list
    ) -> Optional[UUID]:
        """Create a new User + Organization + UserIdentity for a first-time external login."""
        try:
            # Create a new single-user organization
            org = Organization(name=email.split("@")[0] or "Household")
            db.add(org)
            await db.flush()  # get org.id

            # Create user — no password (IdP owns auth)
            is_admin = self.config.admin_group in groups if self.config.admin_group else False
            user = User(
                email=email,
                password_hash=hash_password(secrets.token_urlsafe(32)),  # unusable password
                organization_id=org.id,
                is_org_admin=is_admin,
                is_active=True,
                email_verified=True,  # IdP already verified
            )
            db.add(user)
            await db.flush()  # get user.id

            # Create identity link
            identity = UserIdentity(
                user_id=user.id,
                provider=self.config.provider_name,
                provider_subject=sub,
                provider_email=email,
                provider_groups=groups,
                last_seen_at=utc_now(),
            )
            db.add(identity)

            # Record consent (IdP-provisioned users agree to terms on first login)
            for consent_type in (ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY):
                db.add(
                    UserConsent(
                        user_id=user.id,
                        consent_type=consent_type.value,
                        version=settings.TERMS_VERSION,
                    )
                )

            # Seed default spending categories (same set as /register)
            _default_categories = [
                {"name": "Housing", "color": "#EF5350"},
                {"name": "Groceries", "color": "#66BB6A"},
                {"name": "Dining", "color": "#FFA726"},
                {"name": "Transportation", "color": "#42A5F5"},
                {"name": "Utilities", "color": "#AB47BC"},
                {"name": "Entertainment", "color": "#EC407A"},
                {"name": "Healthcare", "color": "#26A69A"},
                {"name": "Shopping", "color": "#26C6DA"},
            ]
            for _cat in _default_categories:
                db.add(Category(organization_id=org.id, name=_cat["name"], color=_cat["color"]))

            await db.commit()
            logger.info(
                "Auto-provisioned user from %s: user_id=%s",
                self.config.provider_name,
                user.id,
            )
            return user.id

        except Exception:
            await db.rollback()
            logger.exception(
                "Failed to auto-provision user from %s sub=%s",
                self.config.provider_name,
                sub,
            )
            return None
