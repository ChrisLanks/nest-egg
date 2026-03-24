"""Inflation-linked asset tracking and real vs nominal return analysis.

Covers I-Bonds (Series I Savings Bonds) and TIPS (Treasury Inflation-Protected
Securities).

Inflation rates
---------------
CPI data is obtained dynamically via the BLS public API (no API key required):
  https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0

The fetched 12-month trailing CPI-U change is cached in memory for the
process lifetime (re-fetched if older than 24 hours).  If the BLS fetch
fails, the service falls back to the static ``_STATIC_CPI_RATE`` table
defined below and signals ``is_estimated=True`` to callers so the UI can
display a data-staleness notice.

I-Bond composite rate
---------------------
The composite rate = fixed_rate + 2 × semiannual_cpi + fixed_rate × semiannual_cpi
Fixed rate is set by Treasury each May/November.  The current fixed rate is
stored in ``_IBOND_FIXED_RATE_HISTORY`` (static, updated when Treasury
announces new rates — the UI flags it when the value is > 6 months old).

References
----------
- TreasuryDirect I-Bond rate history: https://www.treasurydirect.gov/savings-bonds/i-bonds/i-bond-rate-chart/
- BLS CPI-U series: https://www.bls.gov/cpi/
- TIPS pricing primer: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr294.pdf

DATA MAINTENANCE
----------------
When Treasury announces a new I-Bond fixed rate (May 1 and Nov 1 each year),
add an entry to ``_IBOND_FIXED_RATE_HISTORY`` below.  No other changes needed.
The UI shows "Fixed rate as of MM/YYYY — may be outdated" when the most
recent entry is > 6 months old.
"""

from __future__ import annotations

import logging
import time
import urllib.request
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static fallback CPI rates (trailing 12-month CPI-U % change)
#
# SOURCE: U.S. Bureau of Labor Statistics, All Urban Consumers (CPI-U),
#         not seasonally adjusted, series CUUR0000SA0.
# DATA NOTE: This table is a static fallback used only when the BLS API is
#            unavailable.  The UI surfaces a "CPI data may be outdated" notice
#            when the fallback is active.  Update this table annually or when
#            a significant CPI change occurs.
# ---------------------------------------------------------------------------
_STATIC_CPI_FALLBACK: dict[int, float] = {
    2020: 0.0123,
    2021: 0.0470,
    2022: 0.0800,
    2023: 0.0360,
    2024: 0.0290,
    2025: 0.0270,  # preliminary estimate
}

# ---------------------------------------------------------------------------
# I-Bond fixed rate history (Treasury announces May 1 / Nov 1 each year)
#
# SOURCE: TreasuryDirect.gov I-Bond Rate Chart
# DATA NOTE: Update this dict when Treasury announces new fixed rates.
# Key format: "YYYY-MM" (announcement month)
# ---------------------------------------------------------------------------
_IBOND_FIXED_RATE_HISTORY: dict[str, float] = {
    "2021-05": 0.0000,
    "2021-11": 0.0000,
    "2022-05": 0.0000,
    "2022-11": 0.0040,
    "2023-05": 0.0090,
    "2023-11": 0.0120,
    "2024-05": 0.0130,
    "2024-11": 0.0120,
    "2025-05": 0.0120,  # preliminary — update when Treasury announces
}

# BLS public API — no key required, 25 req/day per IP (unauthenticated)
_BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
_BLS_CPI_SERIES = "CUUR0000SA0"  # CPI-U, all items, not seasonally adjusted

# In-memory cache
_cpi_cache: dict = {"rate": None, "fetched_at": 0.0, "is_estimated": True}
_CACHE_TTL_SECONDS = 86_400  # 24 hours


# ---------------------------------------------------------------------------
# CPI fetch
# ---------------------------------------------------------------------------


def get_current_cpi_rate() -> tuple[float, bool]:
    """Return (trailing_12m_cpi_rate, is_estimated).

    Attempts BLS API first; falls back to static table on any failure.
    ``is_estimated=True`` means the UI should show a data-staleness notice.
    """
    now = time.time()
    cached = _cpi_cache
    if cached["rate"] is not None and (now - cached["fetched_at"]) < _CACHE_TTL_SECONDS:
        return cached["rate"], cached["is_estimated"]

    rate, is_estimated = _fetch_bls_cpi()
    _cpi_cache["rate"] = rate
    _cpi_cache["fetched_at"] = now
    _cpi_cache["is_estimated"] = is_estimated
    return rate, is_estimated


def _fetch_bls_cpi() -> tuple[float, bool]:
    """Hit BLS API for the last 2 years of CPI-U; compute trailing 12m change."""
    try:
        payload = json.dumps({
            "seriesid": [_BLS_CPI_SERIES],
            "startyear": str(date.today().year - 1),
            "endyear": str(date.today().year),
        }).encode()
        req = urllib.request.Request(
            _BLS_API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        series_data = data.get("Results", {}).get("series", [])
        if not series_data:
            raise ValueError("empty BLS response")

        items = series_data[0].get("data", [])
        # items are newest-first; grab the two most-recent annual values
        # (same month, one year apart) to compute year-over-year change
        by_period: dict[str, list[dict]] = {}
        for item in items:
            period = item.get("period", "")
            if period.startswith("M"):  # monthly, not annual
                by_period.setdefault(period, []).append(item)

        # Sort each period list by year descending
        for period in by_period:
            by_period[period].sort(key=lambda x: int(x["year"]), reverse=True)

        # Find a period that has at least 2 years of data
        yoy: Optional[float] = None
        for period, items_list in sorted(by_period.items()):
            if len(items_list) >= 2:
                v_new = float(items_list[0]["value"])
                v_old = float(items_list[1]["value"])
                if v_old > 0:
                    yoy = (v_new - v_old) / v_old
                    break

        if yoy is None:
            raise ValueError("Could not compute YoY CPI from BLS data")

        logger.info("inflation_tracking_service: fetched BLS CPI-U YoY=%.2f%%", yoy * 100)
        return round(yoy, 4), False

    except Exception as exc:
        logger.warning("inflation_tracking_service: BLS fetch failed (%s), using static fallback", exc)
        fallback_year = max(y for y in _STATIC_CPI_FALLBACK if y <= date.today().year)
        return _STATIC_CPI_FALLBACK[fallback_year], True


# ---------------------------------------------------------------------------
# I-Bond calculations
# ---------------------------------------------------------------------------


def get_current_ibond_fixed_rate() -> tuple[float, bool, str]:
    """Return (fixed_rate, is_stale, as_of_label).

    ``is_stale=True`` if the last known rate is > 6 months old.
    """
    today = date.today()
    sorted_keys = sorted(_IBOND_FIXED_RATE_HISTORY.keys(), reverse=True)
    latest_key = sorted_keys[0]
    fixed_rate = _IBOND_FIXED_RATE_HISTORY[latest_key]

    # Parse YYYY-MM
    year, month = int(latest_key[:4]), int(latest_key[5:])
    rate_date = date(year, month, 1)
    months_old = (today.year - rate_date.year) * 12 + (today.month - rate_date.month)
    is_stale = months_old > 6

    return fixed_rate, is_stale, latest_key


def calculate_ibond_composite_rate(
    semiannual_cpi: float,
    fixed_rate: Optional[float] = None,
) -> float:
    """Compute I-Bond composite rate per Treasury formula.

    Composite = fixed_rate + 2 × semiannual_cpi + fixed_rate × semiannual_cpi
    """
    if fixed_rate is None:
        fixed_rate, _, _ = get_current_ibond_fixed_rate()
    composite = fixed_rate + 2 * semiannual_cpi + fixed_rate * semiannual_cpi
    return round(composite, 6)


# ---------------------------------------------------------------------------
# Real vs nominal return conversion
# ---------------------------------------------------------------------------


def nominal_to_real(nominal_return: float, inflation_rate: float) -> float:
    """Fisher equation: (1 + nominal) / (1 + inflation) - 1."""
    if inflation_rate <= -1:
        return nominal_return
    return (1 + nominal_return) / (1 + inflation_rate) - 1


def real_to_nominal(real_return: float, inflation_rate: float) -> float:
    """Inverse Fisher equation: (1 + real) × (1 + inflation) - 1."""
    return (1 + real_return) * (1 + inflation_rate) - 1


# ---------------------------------------------------------------------------
# Inflation-linked account analysis
# ---------------------------------------------------------------------------


@dataclass
class InflationLinkedHolding:
    """Summary of a single inflation-linked account."""

    account_id: str
    account_name: str
    account_type: str  # "tips" | "i_bond"
    current_balance: float

    # I-Bond specific
    ibond_fixed_rate: Optional[float] = None
    ibond_composite_rate: Optional[float] = None

    # Real vs nominal
    nominal_return: Optional[float] = None
    real_return: Optional[float] = None

    # Data quality
    cpi_is_estimated: bool = True
    ibond_rate_is_stale: bool = False
    data_note: str = ""


@dataclass
class InflationTrackingResult:
    """Portfolio-level inflation-linked asset summary."""

    total_inflation_linked: float
    total_portfolio: float
    inflation_linked_pct: float  # percentage of total portfolio

    holdings: list[InflationLinkedHolding]

    # Current CPI
    cpi_rate: float
    cpi_is_estimated: bool

    # I-Bond rates
    ibond_fixed_rate: float
    ibond_composite_rate: float
    ibond_rate_is_stale: bool
    ibond_rate_as_of: str

    # Real return on a generic 7% nominal portfolio
    generic_real_return: float

    data_note: str


def analyze_inflation_linked_accounts(
    accounts: list[dict],  # each: {id, name, account_type, current_balance, nominal_return}
    total_portfolio_value: float,
) -> InflationTrackingResult:
    """Compute inflation-linked tracking metrics for a set of accounts.

    Parameters
    ----------
    accounts:
        List of account dicts with keys: id, name, account_type,
        current_balance, nominal_return (optional, decimal).
    total_portfolio_value:
        Total portfolio value (for percentage calculation).
    """
    cpi_rate, cpi_is_estimated = get_current_cpi_rate()
    semiannual_cpi = (1 + cpi_rate) ** 0.5 - 1  # 6-month CPI component
    fixed_rate, ibond_stale, ibond_as_of = get_current_ibond_fixed_rate()
    composite_rate = calculate_ibond_composite_rate(semiannual_cpi, fixed_rate)

    holdings: list[InflationLinkedHolding] = []
    total_linked = 0.0

    for acct in accounts:
        acct_type = acct.get("account_type", "")
        balance = float(acct.get("current_balance") or 0)
        nom_return = acct.get("nominal_return")

        if acct_type not in ("tips", "i_bond"):
            continue

        total_linked += balance

        real_ret = None
        if nom_return is not None:
            real_ret = round(nominal_to_real(float(nom_return), cpi_rate), 4)

        if acct_type == "i_bond":
            note = (
                f"I-Bond composite rate: {composite_rate*100:.2f}% "
                f"(fixed {fixed_rate*100:.2f}% + inflation component). "
            )
            if ibond_stale:
                note += "⚠ Fixed rate may be outdated — check TreasuryDirect.gov."
            if cpi_is_estimated:
                note += " CPI data is estimated (BLS API unavailable)."
        else:
            note = (
                f"TIPS real yield reflects CPI-adjusted principal. "
                f"Current CPI-U: {cpi_rate*100:.2f}%"
            )
            if cpi_is_estimated:
                note += " (estimated — BLS API unavailable)."

        holdings.append(InflationLinkedHolding(
            account_id=acct.get("id", ""),
            account_name=acct.get("name", ""),
            account_type=acct_type,
            current_balance=balance,
            ibond_fixed_rate=fixed_rate if acct_type == "i_bond" else None,
            ibond_composite_rate=composite_rate if acct_type == "i_bond" else None,
            nominal_return=nom_return,
            real_return=real_ret,
            cpi_is_estimated=cpi_is_estimated,
            ibond_rate_is_stale=ibond_stale if acct_type == "i_bond" else False,
            data_note=note,
        ))

    pct = round(total_linked / total_portfolio_value * 100, 2) if total_portfolio_value > 0 else 0.0
    generic_real = round(nominal_to_real(0.07, cpi_rate), 4)

    portfolio_note = (
        f"CPI-U (trailing 12m): {cpi_rate*100:.2f}%"
        + (" [estimated — BLS API unavailable; static fallback used]" if cpi_is_estimated else "")
        + f". I-Bond fixed rate as of {ibond_as_of}"
        + (" [⚠ may be outdated — check TreasuryDirect.gov]" if ibond_stale else "")
        + "."
    )

    return InflationTrackingResult(
        total_inflation_linked=round(total_linked, 2),
        total_portfolio=round(total_portfolio_value, 2),
        inflation_linked_pct=pct,
        holdings=holdings,
        cpi_rate=cpi_rate,
        cpi_is_estimated=cpi_is_estimated,
        ibond_fixed_rate=fixed_rate,
        ibond_composite_rate=composite_rate,
        ibond_rate_is_stale=ibond_stale,
        ibond_rate_as_of=ibond_as_of,
        generic_real_return=generic_real,
        data_note=portfolio_note,
    )
