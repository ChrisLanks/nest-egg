"""
FX Rate Service
==============
Fetches live exchange rates from Frankfurter (https://www.frankfurter.app),
a free public API backed by the European Central Bank (ECB) daily rates.
No API key required. Rates updated each business day ~4pm CET.

Fallback: returns approximate static mid-2025 rates when API is unreachable.
The caller receives `is_fallback=True` so the UI can display a warning.

Usage:
    from app.services.fx_service import get_rates_with_meta, get_rate, supported_currencies

    result = await get_rates_with_meta("USD")
    # result.rates      — {currency: rate}
    # result.is_fallback — True if live API was unreachable
    # result.data_note  — human-readable warning text when is_fallback

    rate = await get_rate("USD", "EUR")  # e.g. 0.9234 (simple, no meta)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

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


@dataclass
class FXRatesResult:
    rates: dict[str, float]
    is_fallback: bool = False
    data_note: str = ""


async def get_rates_with_meta(base: str = "USD") -> FXRatesResult:
    """
    Fetch all supported exchange rates with *base* as the base currency.
    Results are cached for 1 hour.

    Returns FXRatesResult with is_fallback=True and a data_note warning
    when the live Frankfurter API is unreachable and static rates are used.
    """
    base = base.upper()
    cache_key = f"fx_rates:{base}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return FXRatesResult(rates=cached)

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
        return FXRatesResult(rates=rates)
    except Exception as exc:
        logger.warning("Frankfurter FX fetch failed (base=%s): %s", base, exc)
        # Return fallback rates converted to requested base
        if base == "USD":
            fallback = dict(_FALLBACK_RATES_FROM_USD)
        else:
            usd_to_base = _FALLBACK_RATES_FROM_USD.get(base)
            if usd_to_base and usd_to_base != 0:
                fallback = {k: round(v / usd_to_base, 6) for k, v in _FALLBACK_RATES_FROM_USD.items()}
            else:
                fallback = {base: 1.0}
        return FXRatesResult(
            rates=fallback,
            is_fallback=True,
            data_note="Live rates unavailable (Frankfurter/ECB unreachable) — showing approximate mid-2025 static rates.",
        )


async def get_all_rates(base: str = "USD") -> dict[str, float]:
    """
    Convenience wrapper — returns rates dict only (no fallback metadata).
    Use get_rates_with_meta() when you need to surface a warning to the user.
    """
    result = await get_rates_with_meta(base)
    return result.rates


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
