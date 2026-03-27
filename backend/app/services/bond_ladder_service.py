"""Bond / CD / TIPS Ladder Planning Service.

Builds a ladder of fixed-income instruments maturing at regular intervals
to provide predictable income.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


# Default CD rate estimates (spread above Treasury)
_CD_SPREAD = {
    1: Decimal("0.0010"),   # 10 bps above 1-yr Treasury
    2: Decimal("0.0015"),
    3: Decimal("0.0020"),
    5: Decimal("0.0025"),
    7: Decimal("0.0030"),
    10: Decimal("0.0035"),
}

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


def estimate_cd_rates(treasury_rates: dict) -> dict:
    """Estimate CD rates based on treasury rates + typical spread."""
    cd_rates = {}
    for years, spread in _CD_SPREAD.items():
        maturity_key = _TREASURY_MATURITY_MAP.get(years, "10_year")
        base = treasury_rates.get(maturity_key)
        if base is not None:
            cd_rates[f"{years}_year"] = float(Decimal(str(base)) + spread)
    return cd_rates
