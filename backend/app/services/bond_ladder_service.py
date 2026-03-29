"""Bond / CD / TIPS Ladder Planning Service.

Builds a ladder of fixed-income instruments maturing at regular intervals
to provide predictable income.

Live CD rates are fetched from FRED (St. Louis Federal Reserve) when available:
  CD6NRNJ  — 6-month CD rate (national average, non-jumbo)
  CD1YEAR  — 1-year CD rate (national average, non-jumbo)

Falls back to Treasury spread estimates when FRED is unreachable.
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_CD_6MO_URL = f"{FRED_CSV_BASE}?id=CD6NRNJ"
FRED_CD_1YR_URL = f"{FRED_CSV_BASE}?id=CD1YEAR"
_FRED_TIMEOUT = 8.0

# Default CD rate estimates (spread above Treasury) — used as fallback
_CD_SPREAD = {
    1: Decimal("0.0010"),   # 10 bps above 1-yr Treasury
    2: Decimal("0.0015"),
    3: Decimal("0.0020"),
    5: Decimal("0.0025"),
    7: Decimal("0.0030"),
    10: Decimal("0.0035"),
}

async def _fetch_fred_rate(url: str) -> Optional[float]:
    """Fetch the most recent non-null rate from a FRED public CSV series."""
    try:
        async with httpx.AsyncClient(timeout=_FRED_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        for line in reversed(lines[1:]):
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() not in (".", ""):
                try:
                    return round(float(parts[1].strip()) / 100, 6)
                except ValueError:
                    continue
    except Exception as exc:
        logger.warning("FRED CD rate fetch failed (%s): %s", url, exc)
    return None


async def get_live_cd_rates() -> dict[str, Optional[float]]:
    """
    Fetch live CD rates from FRED.

    Returns dict with keys "6_month" and "1_year" (decimal rates, e.g. 0.045).
    Values are None when FRED is unreachable.
    """
    import asyncio
    rate_6mo, rate_1yr = await asyncio.gather(
        _fetch_fred_rate(FRED_CD_6MO_URL),
        _fetch_fred_rate(FRED_CD_1YR_URL),
    )
    return {"6_month": rate_6mo, "1_year": rate_1yr}


# Map rung year to closest treasury maturity key
_TREASURY_MATURITY_MAP = {
    1: "1_year",
    2: "2_year",
    3: "2_year",   # approximate with 2yr
    4: "5_year",   # approximate with 5yr
    5: "5_year",
    6: "5_year",
    7: "10_year",
    8: "10_year",
    9: "10_year",
    10: "10_year",
}


def _get_rate_for_rung(
    years: int,
    ladder_type: str,
    treasury_rates: dict,
) -> Decimal:
    """Return the annualized yield for a given rung maturity."""
    maturity_key = _TREASURY_MATURITY_MAP.get(years, "10_year")
    base_rate = treasury_rates.get(maturity_key)
    if base_rate is None:
        # Fallback: use a reasonable default
        base_rate = 0.04
    base_rate = Decimal(str(base_rate))

    if ladder_type == "cd":
        spread = _CD_SPREAD.get(years, Decimal("0.0020"))
        return base_rate + spread
    elif ladder_type == "tips":
        # TIPS real yield is typically lower; approximate as treasury - 1%
        tips_adjust = Decimal("0.01")
        return max(base_rate - tips_adjust, Decimal("0.005"))
    else:
        # Treasury — use as-is
        return base_rate


def build_ladder(
    total_investment: Decimal,
    num_rungs: int,
    ladder_type: str,
    start_year: int,
    annual_income_needed: Decimal,
    current_treasury_rates: dict,
) -> dict:
    """Build a bond/CD/TIPS ladder and return per-rung breakdown.

    Parameters
    ----------
    total_investment : Decimal
        Total amount available to invest across all rungs.
    num_rungs : int
        Number of rungs (e.g. 5 for a 5-year ladder).
    ladder_type : str
        One of "cd", "treasury", "tips".
    start_year : int
        Calendar year when the ladder begins.
    annual_income_needed : Decimal
        Desired annual income from the ladder (informational).
    current_treasury_rates : dict
        Treasury rates keyed like {"1_year": 0.045, "2_year": 0.043, ...}.

    Returns
    -------
    dict with keys: rungs, total_interest, total_invested, annual_income_actual,
                    income_vs_needed, reinvestment_note
    """
    if num_rungs < 1:
        num_rungs = 1
    if num_rungs > 30:
        num_rungs = 30

    per_rung = (total_investment / num_rungs).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    rungs = []
    total_interest = Decimal("0")
    total_maturity_values = Decimal("0")

    for i in range(1, num_rungs + 1):
        rate = _get_rate_for_rung(i, ladder_type, current_treasury_rates)
        # Compound interest: FV = PV * (1 + r)^n
        maturity_value = (per_rung * (1 + rate) ** i).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        interest_earned = maturity_value - per_rung
        total_interest += interest_earned
        total_maturity_values += maturity_value

        rungs.append({
            "rung": i,
            "years_to_maturity": i,
            "maturity_year": start_year + i,
            "investment_amount": float(per_rung),
            "annual_rate": float(rate),
            "annual_rate_pct": float((rate * 100).quantize(Decimal("0.01"))),
            "maturity_value": float(maturity_value),
            "interest_earned": float(interest_earned),
            "instrument_type": ladder_type.upper(),
        })

    # Annual income is roughly the average maturity value per year
    annual_income_actual = (total_maturity_values / num_rungs).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    income_gap = float(annual_income_needed) - float(annual_income_actual)

    return {
        "rungs": rungs,
        "num_rungs": num_rungs,
        "ladder_type": ladder_type,
        "total_invested": float(total_investment),
        "per_rung_investment": float(per_rung),
        "total_interest": float(total_interest),
        "total_maturity_values": float(total_maturity_values),
        "annual_income_actual": float(annual_income_actual),
        "annual_income_needed": float(annual_income_needed),
        "income_gap": income_gap,
        "meets_income_target": income_gap <= 0,
        "reinvestment_note": (
            f"As each rung matures, reinvest in a new {num_rungs}-year "
            f"{ladder_type.upper()} to maintain the ladder."
        ),
    }


def estimate_cd_rates(treasury_rates: dict, live_cd_rates: Optional[dict] = None) -> dict:
    """
    Estimate CD rates based on treasury rates + typical spread.

    If live_cd_rates is provided (from get_live_cd_rates()), those are used
    directly for the maturities they cover (6-month, 1-year) and spread
    estimates fill in the rest.
    """
    cd_rates = {}
    for years, spread in _CD_SPREAD.items():
        maturity_key = _TREASURY_MATURITY_MAP.get(years, "10_year")
        base = treasury_rates.get(maturity_key)
        if base is not None:
            cd_rates[f"{years}_year"] = float(Decimal(str(base)) + spread)

    # Override with live FRED rates where available
    if live_cd_rates:
        if live_cd_rates.get("6_month") is not None:
            cd_rates["6_month"] = live_cd_rates["6_month"]
        if live_cd_rates.get("1_year") is not None:
            cd_rates["1_year"] = live_cd_rates["1_year"]

    return cd_rates
