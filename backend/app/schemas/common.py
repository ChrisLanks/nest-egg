"""Shared Pydantic models used across multiple endpoints."""

from typing import Optional

from pydantic import BaseModel


class DataSourceMeta(BaseModel):
    """Metadata about the data source for an API response.

    source values:
      - "live"           — fetched from an authoritative API (IRS, SSA, CMS)
      - "cached"         — previously fetched, served from Redis cache
      - "static_YYYY"    — hardcoded constants from financial.py for tax year YYYY

    The frontend should show a banner when source != "live".
    """

    source: str  # "live", "cached", "static_YYYY"
    as_of: str  # ISO date string
    note: Optional[str] = None
    cache_expires: Optional[str] = None
