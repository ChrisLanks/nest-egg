"""Base classes for identity providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AuthenticatedIdentity:
    """Normalized identity returned by any identity provider after successful validation.

    ``user_id`` is resolved from the app database. For built-in tokens it maps
    directly from the JWT ``sub`` claim. For external OIDC providers it is looked
    up (and optionally created) via the ``user_identities`` table.

    ``None`` should only occur transiently during auto-provisioning; ``get_chain``
    always returns an identity with a resolved user_id or raises 401.
    """

    user_id: Optional[UUID]
    provider: str           # 'builtin', 'cognito', 'keycloak', 'okta', 'google'
    subject: str            # IdP's stable sub claim
    email: str
    groups: list = field(default_factory=list)  # IdP group memberships
    raw_claims: dict = field(default_factory=dict)


class IdentityProvider(ABC):
    """Abstract base for all identity providers."""

    provider_name: ClassVar[str]

    @abstractmethod
    def can_handle(self, token: str) -> bool:
        """Fast pre-check: does this JWT look like it belongs to this provider?

        Should be cheap (just inspect the unverified header / iss claim).
        Must not raise — return False on any parse error.
        """

    @abstractmethod
    async def validate_token(
        self, token: str, db: AsyncSession
    ) -> Optional[AuthenticatedIdentity]:
        """Fully validate the token and return an authenticated identity.

        Returns ``None`` if the token cannot be validated (wrong key, wrong
        audience, etc.) so the chain can try the next provider.
        Raises ``HTTPException(401)`` only for tokens that *should* be valid
        but are expired or revoked — to give the user an actionable error.
        """
