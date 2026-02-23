"""Identity provider package — authentication abstraction layer."""

from app.services.identity.base import AuthenticatedIdentity, IdentityProvider
from app.services.identity.builtin import BuiltinIdentityProvider
from app.services.identity.chain import (
    IdentityProviderChain,
    build_chain,
    get_chain,
    reset_chain,
)
from app.services.identity.oidc import OIDCIdentityProvider, OIDCProviderConfig

__all__ = [
    "AuthenticatedIdentity",
    "IdentityProvider",
    "BuiltinIdentityProvider",
    "OIDCIdentityProvider",
    "OIDCProviderConfig",
    "IdentityProviderChain",
    "build_chain",
    "get_chain",
    "reset_chain",
]
