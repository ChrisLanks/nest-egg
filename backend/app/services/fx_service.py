"""
FX Rate Service
==============
Stub that returns 1.0 for all currency pairs until a real FX API is integrated.

When a live FX API (e.g. Open Exchange Rates, ECB, Frankfurter) is plugged in,
replace `get_rate()` with an async HTTP call + Redis cache (TTL ~1h recommended).

Usage:
    from app.services.fx_service import get_rate, supported_currencies

    rate = await get_rate("USD", "EUR")   # 1.0 until API integrated
    amount_eur = amount_usd * rate
"""

from __future__ import annotations

SUPPORTED_CURRENCIES: list[str] = [
    "USD",
    "EUR",
    "GBP",
    "CAD",
    "AUD",
    "JPY",
    "CHF",
    "INR",
    "MXN",
    "BRL",
]


async def get_rate(from_currency: str, to_currency: str) -> float:
    """
    Return the exchange rate from *from_currency* to *to_currency*.

    Currently returns 1.0 for all pairs (no conversion).
    When an FX API is integrated, this function will fetch and cache live rates.
    """
    if from_currency.upper() == to_currency.upper():
        return 1.0
    # TODO: integrate a live FX API here (e.g. Frankfurter, Open Exchange Rates)
    return 1.0


def supported_currencies() -> list[str]:
    """Return the list of ISO 4217 currency codes supported by this app."""
    return list(SUPPORTED_CURRENCIES)
