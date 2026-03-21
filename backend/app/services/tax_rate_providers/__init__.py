"""Tax rate provider registry.

Usage
-----
    from app.services.tax_rate_providers import get_provider

    provider = await get_provider()
    rate = await provider.get_rate("CA", "single", 75000)

To override the active provider (testing or custom deployments)::

    from app.services.tax_rate_providers import set_provider
    from app.services.tax_rate_providers.static_provider import StaticStateTaxProvider

    set_provider(StaticStateTaxProvider())
"""

from app.services.tax_rate_providers.base import StateTaxBracket, StateTaxProvider
from app.services.tax_rate_providers.static_provider import StaticStateTaxProvider
from app.services.tax_rate_providers.taxgraphs_provider import TaxGraphsProvider

_provider: StateTaxProvider | None = None


async def get_provider() -> StateTaxProvider:
    """Return the active provider, initialising TaxGraphsProvider on first call."""
    global _provider
    if _provider is None:
        _provider = TaxGraphsProvider()
    return _provider


def set_provider(provider: StateTaxProvider) -> None:
    """Override the active provider (for testing or custom deployments)."""
    global _provider
    _provider = provider


__all__ = [
    "StateTaxBracket",
    "StateTaxProvider",
    "StaticStateTaxProvider",
    "TaxGraphsProvider",
    "get_provider",
    "set_provider",
]
