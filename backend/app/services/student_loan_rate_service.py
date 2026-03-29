"""
Student Loan Rate Service
=========================
Fetches current federal student loan interest rates.

Federal student loan rates are set annually by Congress each July 1st,
tied to the 10-year Treasury note yield at the May auction plus a fixed
statutory add-on (spread). Since FRED discontinued the SLOAS series, we
derive current rates from the 10-year Treasury yield using the statutory
formulas, with hardcoded confirmed values as a baseline.

Statutory formulas (set by Congress, fixed by law):
  Undergraduate Direct Subsidized/Unsubsidized: 10-yr T-note + 2.05%, cap 8.25%
  Graduate Direct Unsubsidized:                 10-yr T-note + 3.60%, cap 9.50%
  Parent/Grad PLUS:                             10-yr T-note + 4.60%, cap 10.50%

Rates are fixed for each academic year's loans but new loans each July get
the new rate. This service reports the current-year statutory rates.

Sources:
  - studentaid.gov for confirmed annual rates
  - FRED THREEFY10 (10-yr Treasury CMT May auction) for derivation
  - Statutory formulas: 20 U.S.C. § 1087E(b)
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
# 10-year Treasury constant maturity rate (monthly) — used for formula derivation
FRED_10YR_URL = f"{FRED_CSV_BASE}?id=DGS10"
_TIMEOUT = 8.0

# Statutory add-ons and caps (fixed by Congress, do not change year-to-year)
_UNDERGRAD_ADDON = 2.05  # percentage points
_GRAD_ADDON = 3.60
_PLUS_ADDON = 4.60
_UNDERGRAD_CAP = 8.25
_GRAD_CAP = 9.50
_PLUS_CAP = 10.50

# Confirmed academic-year rates from studentaid.gov
# Format: {academic_year_start: {type: rate_pct}}
# AY 2024-25 (July 1, 2024 — June 30, 2025): based on May 2024 T-note ~4.484%
# AY 2025-26 (July 1, 2025 — June 30, 2026): based on May 2025 T-note ~4.48%
_CONFIRMED_RATES: dict[int, dict[str, float]] = {
    2023: {
        "undergrad_subsidized": 5.50,
        "undergrad_unsubsidized": 5.50,
        "grad_unsubsidized": 7.05,
        "parent_plus": 8.05,
        "grad_plus": 8.05,
    },
    2024: {
        "undergrad_subsidized": 6.53,
        "undergrad_unsubsidized": 6.53,
        "grad_unsubsidized": 8.08,
        "parent_plus": 9.08,
        "grad_plus": 9.08,
    },
    2025: {
        "undergrad_subsidized": 6.53,
        "undergrad_unsubsidized": 6.53,
        "grad_unsubsidized": 8.08,
        "parent_plus": 9.08,
        "grad_plus": 9.08,
    },
}


class StudentLoanRates(BaseModel):
    academic_year: str  # e.g. "2025-26"
    undergrad_subsidized: float  # %
    undergrad_unsubsidized: float  # %
    grad_unsubsidized: float  # %
    parent_plus: float  # %
    grad_plus: float  # %
    source: str = "studentaid.gov / statutory formula"
    derived: bool = False  # True if computed from T-note formula vs confirmed


def _current_academic_year() -> int:
    """Return the start year of the current academic year (July-June cycle)."""
    import datetime
    today = datetime.date.today()
    return today.year if today.month >= 7 else today.year - 1


def _apply_formula(t10_pct: float) -> dict[str, float]:
    """Apply congressional statutory formulas to a 10-yr Treasury rate (%)."""
    undergrad = min(round(t10_pct + _UNDERGRAD_ADDON, 2), _UNDERGRAD_CAP)
    grad = min(round(t10_pct + _GRAD_ADDON, 2), _GRAD_CAP)
    plus = min(round(t10_pct + _PLUS_ADDON, 2), _PLUS_CAP)
    return {
        "undergrad_subsidized": undergrad,
        "undergrad_unsubsidized": undergrad,
        "grad_unsubsidized": grad,
        "parent_plus": plus,
        "grad_plus": plus,
    }


async def _fetch_10yr_treasury_rate() -> Optional[float]:
    """Fetch the most recent 10-year Treasury CMT rate from FRED (percent)."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(FRED_10YR_URL)
            resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        for line in reversed(lines[1:]):
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() not in (".", ""):
                try:
                    return float(parts[1].strip())
                except ValueError:
                    continue
    except Exception as exc:
        logger.warning("FRED 10yr Treasury fetch failed: %s", exc)
    return None


async def get_student_loan_rates() -> StudentLoanRates:
    """
    Return current federal student loan interest rates.

    Uses confirmed academic-year rates from studentaid.gov when available.
    Falls back to deriving rates from the current 10-year Treasury CMT rate
    using the statutory formula when the current academic year is not yet
    confirmed.
    """
    import datetime
    ay_start = _current_academic_year()
    ay_label = f"{ay_start}-{str(ay_start + 1)[-2:]}"

    if ay_start in _CONFIRMED_RATES:
        rates = _CONFIRMED_RATES[ay_start]
        return StudentLoanRates(
            academic_year=ay_label,
            undergrad_subsidized=rates["undergrad_subsidized"],
            undergrad_unsubsidized=rates["undergrad_unsubsidized"],
            grad_unsubsidized=rates["grad_unsubsidized"],
            parent_plus=rates["parent_plus"],
            grad_plus=rates["grad_plus"],
            derived=False,
        )

    # Not yet confirmed — derive from live 10-yr Treasury + statutory formula
    t10 = await _fetch_10yr_treasury_rate()
    if t10 is not None:
        rates = _apply_formula(t10)
        return StudentLoanRates(
            academic_year=ay_label,
            undergrad_subsidized=rates["undergrad_subsidized"],
            undergrad_unsubsidized=rates["undergrad_unsubsidized"],
            grad_unsubsidized=rates["grad_unsubsidized"],
            parent_plus=rates["parent_plus"],
            grad_plus=rates["grad_plus"],
            source="Derived: 10-yr Treasury (FRED) + statutory add-on",
            derived=True,
        )

    # Final fallback: most recent confirmed year
    most_recent_ay = max(_CONFIRMED_RATES.keys())
    rates = _CONFIRMED_RATES[most_recent_ay]
    ay_label = f"{most_recent_ay}-{str(most_recent_ay + 1)[-2:]}"
    return StudentLoanRates(
        academic_year=ay_label,
        undergrad_subsidized=rates["undergrad_subsidized"],
        undergrad_unsubsidized=rates["undergrad_unsubsidized"],
        grad_unsubsidized=rates["grad_unsubsidized"],
        parent_plus=rates["parent_plus"],
        grad_plus=rates["grad_plus"],
        source="studentaid.gov (fallback — current AY not yet confirmed)",
        derived=False,
    )
