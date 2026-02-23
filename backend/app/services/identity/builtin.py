"""Built-in identity provider — validates the app's own HS256 JWTs."""

import logging
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt as jose_jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.services.identity.base import AuthenticatedIdentity, IdentityProvider

logger = logging.getLogger(__name__)


class BuiltinIdentityProvider(IdentityProvider):
    """Validates HS256 JWTs issued by this application.

    This is the default provider used in development and self-hosted deployments
    with no external IdP configured. It wraps the existing ``decode_token()``
    function so that the built-in auth path is unchanged.
    """

    provider_name = "builtin"

    def can_handle(self, token: str) -> bool:
        """Return True if the token uses HS256 (app-issued)."""
        try:
            header = jose_jwt.get_unverified_header(token)
            return header.get("alg") == "HS256"
        except Exception:
            return False

    async def validate_token(
        self, token: str, db: AsyncSession
    ) -> Optional[AuthenticatedIdentity]:
        """Validate HS256 token using the app secret key."""
        try:
            payload = decode_token(token)
        except JWTError:
            return None
        except Exception:
            return None

        if payload.get("type") != "access":
            return None

        sub = payload.get("sub")
        if not sub:
            return None

        try:
            user_id = UUID(sub)
        except ValueError:
            return None

        return AuthenticatedIdentity(
            user_id=user_id,
            provider=self.provider_name,
            subject=sub,
            email=payload.get("email", ""),
            groups=[],
            raw_claims=payload,
        )
