"""
Auto-valuation service for property and vehicle accounts.

Supported providers
───────────────────
Property
  rentcast  → RentCast AVM (rentcast.io)               requires RENTCAST_API_KEY
              Free tier: 50 calls/month — sufficient for personal finance use
              RECOMMENDED: official API, free tier, no ToS concerns
  attom     → ATTOM Data API (attomdata.com)           requires ATTOM_API_KEY
              Paid after 30-day trial
  zillow    → Zillow Zestimate via unofficial RapidAPI  requires ZILLOW_RAPIDAPI_KEY
              NOT RECOMMENDED — unofficial third-party scraper on RapidAPI
              (zillow-com1.p.rapidapi.com). Zillow's official Zestimate API is
              restricted to MLS partners. Using this wrapper may violate Zillow's
              Terms of Service. Use at your own risk.

Vehicle
  marketcheck → MarketCheck (marketcheck.com)          requires MARKETCHECK_API_KEY
                VIN-based used-car market value

Free utility (no key required)
  NHTSA VIN decode → year / make / model (no price)

When no provider key is configured the service returns None and the account
balance must be updated manually. The API exposes a /valuation-providers
discovery endpoint so the UI can show or hide the refresh button accordingly.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

import httpx

from app.config import settings

# VIN format: exactly 17 alphanumeric characters, excluding I, O, Q
_VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0)


# ── result type ───────────────────────────────────────────────────────────────

@dataclass
class ValuationResult:
    value: Decimal
    provider: str
    low: Optional[Decimal] = None
    high: Optional[Decimal] = None


# ── provider discovery ────────────────────────────────────────────────────────

def get_available_property_providers() -> list[str]:
    """Return the list of configured property valuation providers."""
    providers = []
    if settings.RENTCAST_API_KEY:
        providers.append("rentcast")
    if settings.ATTOM_API_KEY:
        providers.append("attom")
    if settings.ZILLOW_RAPIDAPI_KEY:
        providers.append("zillow")
    return providers


def get_available_vehicle_providers() -> list[str]:
    """Return the list of configured vehicle valuation providers."""
    providers = []
    if settings.MARKETCHECK_API_KEY:
        providers.append("marketcheck")
    return providers


# ── property providers ────────────────────────────────────────────────────────

async def _get_property_value_rentcast(address: str, zip_code: str) -> Optional[ValuationResult]:
    """
    Fetch AVM estimate via RentCast API.

    Free tier: 50 API calls/month (permanent).
    Endpoint: GET https://api.rentcast.io/v1/avm/value
    Docs: developers.rentcast.io/reference/property-valuation
    """
    url = "https://api.rentcast.io/v1/avm/value"
    headers = {
        "X-Api-Key": settings.RENTCAST_API_KEY,
        "Accept": "application/json",
    }
    params = {"address": address, "zipCode": zip_code}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        price = data.get("price")
        if price is None:
            logger.warning("rentcast: no price returned for %s %s", address, zip_code)
            return None

        logger.info("rentcast: %s %s → %s", address, zip_code, price)
        return ValuationResult(
            value=Decimal(str(price)),
            provider="rentcast",
            low=Decimal(str(data["priceRangeLow"])) if data.get("priceRangeLow") else None,
            high=Decimal(str(data["priceRangeHigh"])) if data.get("priceRangeHigh") else None,
        )

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "rentcast: HTTP %s for %s %s: %s",
            exc.response.status_code, address, zip_code, exc.response.text[:200],
        )
        return None
    except Exception as exc:
        logger.warning("rentcast: unexpected error: %s", exc)
        return None


async def _get_property_value_attom(address: str, zip_code: str) -> Optional[ValuationResult]:
    """
    Fetch AVM estimate via ATTOM Data API.

    Endpoint: GET https://api.gateway.attomdata.com/propertyapi/v1.0.0/avm/detail
    Docs: developer.attomdata.com
    """
    url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/avm/detail"
    headers = {
        "apikey": settings.ATTOM_API_KEY,
        "Accept": "application/json",
    }
    params = {"address1": address, "address2": zip_code}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        properties = data.get("property", [])
        if not properties:
            logger.warning("attom: no property found for %s %s", address, zip_code)
            return None

        avm = properties[0].get("avm", {})
        amount = avm.get("amount", {})
        value = amount.get("value")
        if value is None:
            logger.warning("attom: AVM value missing for %s %s", address, zip_code)
            return None

        logger.info("attom: %s %s → %s", address, zip_code, value)
        low = amount.get("low")
        high = amount.get("high")
        return ValuationResult(
            value=Decimal(str(value)),
            provider="attom",
            low=Decimal(str(low)) if low is not None else None,
            high=Decimal(str(high)) if high is not None else None,
        )

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "attom: HTTP %s for %s %s: %s",
            exc.response.status_code, address, zip_code, exc.response.text[:200],
        )
        return None
    except Exception as exc:
        logger.warning("attom: unexpected error: %s", exc)
        return None


async def _get_property_value_zillow(address: str, zip_code: str) -> Optional[ValuationResult]:
    """
    Fetch Zestimate via an unofficial RapidAPI wrapper for Zillow.

    NOT RECOMMENDED — Zillow's official Zestimate API is restricted to MLS
    partners. This uses a third-party RapidAPI scraper and may violate Zillow's
    Terms of Service. Use at your own risk.

    Wrapper: zillow-com1.p.rapidapi.com
    Endpoint: GET /valueEstimate
    """
    url = "https://zillow-com1.p.rapidapi.com/valueEstimate"
    headers = {
        "X-RapidAPI-Key": settings.ZILLOW_RAPIDAPI_KEY,
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
        "Accept": "application/json",
    }
    params = {"address": f"{address} {zip_code}".strip()}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        zestimate = data.get("zestimate")
        if zestimate is None:
            logger.warning("zillow: no zestimate returned for %s %s", address, zip_code)
            return None

        logger.info("zillow: %s %s → %s", address, zip_code, zestimate)
        low = data.get("valuationRangeLow")
        high = data.get("valuationRangeHigh")
        return ValuationResult(
            value=Decimal(str(zestimate)),
            provider="zillow",
            low=Decimal(str(low)) if low is not None else None,
            high=Decimal(str(high)) if high is not None else None,
        )

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "zillow: HTTP %s for %s %s: %s",
            exc.response.status_code, address, zip_code, exc.response.text[:200],
        )
        return None
    except Exception as exc:
        logger.warning("zillow: unexpected error: %s", exc)
        return None


_PROPERTY_PROVIDERS = {
    "rentcast": _get_property_value_rentcast,
    "attom": _get_property_value_attom,
    "zillow": _get_property_value_zillow,
}


async def get_property_value(
    address: str,
    zip_code: str,
    provider: Optional[str] = None,
) -> Optional[ValuationResult]:
    """
    Fetch property AVM using the specified provider, or the first available one.

    Returns None when no provider is configured or all calls fail.
    """
    if provider:
        if provider not in _PROPERTY_PROVIDERS:
            logger.warning("get_property_value: unknown provider %r", provider)
            return None
        fn = _PROPERTY_PROVIDERS[provider]
        if not _is_provider_configured(provider):
            logger.warning("get_property_value: provider %r not configured", provider)
            return None
        return await fn(address, zip_code)

    # Auto-select first available
    for name in get_available_property_providers():
        result = await _PROPERTY_PROVIDERS[name](address, zip_code)
        if result is not None:
            return result

    return None


# ── vehicle providers ─────────────────────────────────────────────────────────

async def decode_vin_nhtsa(vin: str) -> Optional[dict]:
    """
    Decode a VIN via the free NHTSA API (no key required).

    Returns a dict with year, make, model (no price).
    Always free and official.
    """
    # Validate VIN format to prevent path traversal in URL
    if not _VIN_RE.match(vin.upper()):
        logger.warning("Invalid VIN format: %s", vin[:20])
        return None
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        results = {
            r["Variable"]: r["Value"]
            for r in data.get("Results", [])
            if r.get("Value") not in (None, "")
        }
        return {
            "year": results.get("Model Year"),
            "make": results.get("Make"),
            "model": results.get("Model"),
            "trim": results.get("Trim"),
            "body_style": results.get("Body Class"),
        }
    except Exception as exc:
        logger.warning("vin_decode failed for %s: %s", vin, exc)
        return None


async def _get_vehicle_value_marketcheck(
    vin: str,
    mileage: Optional[int] = None,
) -> Optional[ValuationResult]:
    """
    Fetch used-car market value via MarketCheck API.

    Endpoint: GET https://mc-api.marketcheck.com/v2/predict/car/marketvalue
    Docs: apidocs.marketcheck.com
    """
    url = "https://mc-api.marketcheck.com/v2/predict/car/marketvalue"
    params: dict = {"api_key": settings.MARKETCHECK_API_KEY, "vin": vin}
    if mileage:
        params["miles"] = mileage

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        price = data.get("price", {})
        mean = price.get("mean")
        if mean is None:
            logger.warning("marketcheck: no mean price for VIN %s", vin)
            return None

        logger.info("marketcheck: vin=%s → %s", vin, mean)
        return ValuationResult(
            value=Decimal(str(mean)),
            provider="marketcheck",
            low=Decimal(str(price["low"])) if price.get("low") is not None else None,
            high=Decimal(str(price["high"])) if price.get("high") is not None else None,
        )

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "marketcheck: HTTP %s for VIN %s: %s",
            exc.response.status_code, vin, exc.response.text[:200],
        )
        return None
    except Exception as exc:
        logger.warning("marketcheck: unexpected error: %s", exc)
        return None


_VEHICLE_PROVIDERS = {
    "marketcheck": _get_vehicle_value_marketcheck,
}


async def get_vehicle_value(
    vin: str,
    mileage: Optional[int] = None,
    provider: Optional[str] = None,
) -> Optional[ValuationResult]:
    """
    Fetch vehicle market value using the specified provider, or the first available one.
    """
    if provider:
        if provider not in _VEHICLE_PROVIDERS:
            logger.warning("get_vehicle_value: unknown provider %r", provider)
            return None
        if not _is_provider_configured(provider):
            logger.warning("get_vehicle_value: provider %r not configured", provider)
            return None
        return await _VEHICLE_PROVIDERS[provider](vin, mileage)

    for name in get_available_vehicle_providers():
        result = await _VEHICLE_PROVIDERS[name](vin, mileage)
        if result is not None:
            return result

    return None


# ── internal helpers ──────────────────────────────────────────────────────────

def _is_provider_configured(provider: str) -> bool:
    key_map = {
        "rentcast": settings.RENTCAST_API_KEY,
        "attom": settings.ATTOM_API_KEY,
        "zillow": settings.ZILLOW_RAPIDAPI_KEY,
        "marketcheck": settings.MARKETCHECK_API_KEY,
    }
    return bool(key_map.get(provider))
