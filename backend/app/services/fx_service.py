"""
FX Rate Service
==============
Fetches live exchange rates from Frankfurter (https://www.frankfurter.app),
a free public API backed by the European Central Bank (ECB) daily rates.
No API key required. Rates updated each business day ~4pm CET.

Fallback: returns 1.0 (no conversion) if the API is unreachable.

Usage:
    from app.services.fx_service import get_rate, get_all_rates, supported_currencies

    rate = await get_rate("USD", "EUR")           # e.g. 0.9234
    rates = await get_all_rates("USD")            # all pairs vs USD
    amount_eur = amount_usd * rate
"""

from __future__ import annotations

import logging

import httpx

from app.core.cache import get as cache_get
from app.core.cache import setex as cache_setex

logger = logging.getLogger(__name__)

_FRANKFURTER_URL = "https://api.frankfurter.app/latest"
_TIMEOUT = 6.0
_CACHE_TTL = 3600  # 1 hour — ECB updates once per business day

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

# Fallback rates (approximate mid-2025 values) used when API is unreachable
_FALLBACK_RATES_FROM_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.36,
    "AUD": 1.54,
    "JPY": 149.0,
    "CHF": 0.89,
    "INR": 83.5,
    "MXN": 17.2,
    "BRL": 5.0,
}


async def get_all_rates(base: str = "USD") -> dict[str, float]:
    """
    Fetch all supported exchange rates with *base* as the base currency.
    Results are cached for 1 hour.

    Returns a dict of {currency_code: rate} including the base currency (1.0).
    On failure, returns approximate fallback rates.
    """
    base = base.upper()
    cache_key = f"fx_rates:{base}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    symbols = ",".join(c for c in SUPPORTED_CURRENCIES if c != base)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _FRANKFURTER_URL,
                params={"base": base, "symbols": symbols},
            )
            resp.raise_for_status()
        data = resp.json()
        rates: dict[str, float] = {base: 1.0}
        rates.update({k: float(v) for k, v in data.get("rates", {}).items()})
        await cache_setex(cache_key, _CACHE_TTL, rates)
        return rates
    except Exception as exc:
        logger.warning("Frankfurter FX fetch failed (base=%s): %s", base, exc)
        # Return fallback rates converted to requested base
        if base == "USD":
            return dict(_FALLBACK_RATES_FROM_USD)
        usd_to_base = _FALLBACK_RATES_FROM_USD.get(base)
        if usd_to_base and usd_to_base != 0:
            return {k: round(v / usd_to_base, 6) for k, v in _FALLBACK_RATES_FROM_USD.items()}
        return {base: 1.0}


async def get_rate(from_currency: str, to_currency: str) -> float:
    """
    Return the exchange rate from *from_currency* to *to_currency*.
    Fetches from Frankfurter (ECB) with 1-hour Redis cache.
    Falls back to approximate static rates if the API is unreachable.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0

    rates = await get_all_rates(from_currency)
    return rates.get(to_currency, 1.0)


def supported_currencies() -> list[str]:
    """Return the list of ISO 4217 currency codes supported by this app."""
    return list(SUPPORTED_CURRENCIES)
