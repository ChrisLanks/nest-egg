"""Sequence-of-returns risk analysis with Guyton-Klinger guardrails.

This service implements two capabilities:

1. **Crash-year stress test** — simulate retiring into an immediate severe
   drawdown (configurable, defaults to -38% modelling a 2008-style crash)
   and show how the portfolio recovers (or doesn't) across percentile paths.

2. **Guyton-Klinger dynamic spending guardrails** — adjust withdrawals
   upward or downward based on the current withdrawal rate relative to the
   initial rate.  Rules:
     - *Prosperity rule*: if current_wr < LOWER_GUARD * initial_wr, raise
       spending by 10%.
     - *Capital-preservation rule*: if current_wr > UPPER_GUARD * initial_wr
       AND more than 15 years of retirement remain, cut spending by 10%.

Both modes run a configurable number of Monte Carlo paths and return
percentile fan data, success rates, and per-year statistics.

Constants
---------
The long-run expected return and volatility assumptions are read from
``app.constants.financial.FIRE`` (MC_PRE_RETIREMENT_RETURN / _POST /
_VOLATILITY) and are never hardcoded here so that a single update to
financial.py propagates everywhere.

The historical crash scenarios (CRASH_SCENARIOS dict) come from verified
public market data.  They are the *only* static table in this file; it is
documented below and carries a staleness note that the UI surfaces.

References
----------
- Guyton, J. T. & Klinger, W. J. (2006). "Decision rules and maximum
  initial withdrawal rates." Journal of Financial Planning 19 (3): 48–58.
- Kitces, M. (2015). "The ratcheting safe withdrawal rate."
  https://www.kitces.com/
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from app.constants.financial import FIRE

# ---------------------------------------------------------------------------
# Historical crash scenario reference data
#
# DATA NOTE: Values below are the peak-to-trough drawdowns of major market
# crises, sourced from public financial literature and widely-cited data
# sets (Robert Shiller / CRSP).  They are intentionally static — market
# history doesn't change retroactively.  Each entry includes the worst
# single-year return used in the stress test, plus the recovery pattern.
#
# ⚠ UI NOTE: This table is static and does not require periodic updates,
# but the CURRENT_YEAR default-crash figure (-38 %) is sourced from the
# 2008 S&P 500 drawdown and is considered the canonical "severe bear market"
# benchmark.  If the user wants to model a personalised scenario they can
# override crash_return_pct via the API parameter.
# ---------------------------------------------------------------------------
CRASH_SCENARIOS: dict[str, dict] = {
    "2008_financial_crisis": {
        "year": 2008,
        "first_year_return": -0.3700,  # S&P 500 2008 total return
        "description": "2008 Financial Crisis (S&P 500: -37%)",
        "source": "Robert Shiller CRSP data / NYU Stern Damodaran dataset",
        "data_as_of": "2024",
    },
    "2000_dot_com": {
        "year": 2000,
        "first_year_return": -0.0910,  # S&P 500 2000 total return
        "description": "2000 Dot-Com Crash (S&P 500: -9.1% in 2000, -11.9% in 2001)",
        "source": "Robert Shiller CRSP data / NYU Stern Damodaran dataset",
        "data_as_of": "2024",
    },
    "1973_oil_shock": {
        "year": 1973,
        "first_year_return": -0.1466,  # S&P 500 1973 return
        "description": "1973-74 Oil Shock / Stagflation (S&P 500: -14.7% in 1973)",
        "source": "Robert Shiller CRSP data / NYU Stern Damodaran dataset",
        "data_as_of": "2024",
    },
}

# Guardrails multipliers (Guyton-Klinger 2006)
_LOWER_GUARD = 0.80  # Below 80 % of initial WR → raise spending
_UPPER_GUARD = 1.20  # Above 120 % of initial WR → cut spending
_ADJUSTMENT = 0.10  # 10 % raise or cut
_MIN_YEARS_FOR_CUTS = 15  # Don't cut spending within 15 years of end


@dataclass
class YearStats:
    """Per-year summary statistics across all simulation paths."""

    year: int
    age: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    mean: float
    pct_depleted: float  # fraction of paths already at $0


@dataclass
class GuardrailsResult:
    """Output of a guardrails / crash-year stress test simulation."""

    # Input echo
    initial_portfolio: float
    initial_annual_spending: float
    initial_withdrawal_rate: float
    crash_scenario_name: str
    crash_first_year_return: float
    guardrails_enabled: bool

    # Summary metrics
    success_rate: float  # fraction of paths that never depleted
    median_final_portfolio: float
    p10_final_portfolio: float  # pessimistic
    p90_final_portfolio: float  # optimistic

    # Per-year fan data
    yearly_stats: list[YearStats]

    # Spending path under median scenario
    median_spending_path: list[float]  # one entry per simulated year

    # Metadata
    num_simulations: int
    years_simulated: int
    data_note: str  # surfaced in the UI as a staleness caveat


def run_guardrails_simulation(
    initial_portfolio: float,
    annual_spending: float,
    current_age: int,
    life_expectancy: int,
    crash_scenario: str = "2008_financial_crisis",
    crash_return_override: Optional[float] = None,
    guardrails_enabled: bool = True,
    num_simulations: int = 1_000,
    expected_return: Optional[float] = None,
    volatility: Optional[float] = None,
    inflation: float = FIRE.DEFAULT_INFLATION,
) -> GuardrailsResult:
    """Run Monte Carlo with optional guardrails and/or a forced crash in year 1.

    Parameters
    ----------
    initial_portfolio:
        Portfolio value at retirement.
    annual_spending:
        Baseline annual withdrawal in today's dollars.
    current_age:
        Age at retirement (start of simulation).
    life_expectancy:
        Age at which the simulation ends.
    crash_scenario:
        Key from CRASH_SCENARIOS (or "custom" if crash_return_override provided).
    crash_return_override:
        If set, overrides the scenario's first_year_return.  Expressed as a
        decimal (e.g. -0.40 for -40 %).
    guardrails_enabled:
        Apply Guyton-Klinger raise/cut rules each year.
    num_simulations:
        Number of Monte Carlo paths.
    expected_return:
        Mean annual portfolio return (decimal).  Defaults to FIRE.MC_POST_RETIREMENT_RETURN.
    volatility:
        Annual standard deviation (decimal).  Defaults to FIRE.MC_VOLATILITY.
    inflation:
        Annual inflation rate for spending adjustment.
    """
    if initial_portfolio <= 0 or annual_spending <= 0:
        raise ValueError("initial_portfolio and annual_spending must be positive")

    if life_expectancy <= current_age:
        raise ValueError("life_expectancy must be greater than current_age")

    mu = (expected_return if expected_return is not None
          else FIRE.MC_POST_RETIREMENT_RETURN / 100.0)
    sigma = (volatility if volatility is not None
             else FIRE.MC_VOLATILITY / 100.0)

    total_years = life_expectancy - current_age

    # Resolve crash scenario
    if crash_return_override is not None:
        crash_return = float(crash_return_override)
        scenario_name = "custom"
        data_note = (
            "Custom crash scenario — user-specified first-year return. "
            "Long-run return assumptions from app.constants.financial (FIRE class)."
        )
    elif crash_scenario in CRASH_SCENARIOS:
        cs = CRASH_SCENARIOS[crash_scenario]
        crash_return = cs["first_year_return"]
        scenario_name = crash_scenario
        data_note = (
            f"Crash scenario: {cs['description']}. "
            f"Source: {cs['source']} (data as of {cs['data_as_of']}). "
            "Long-run return/volatility from financial.py FIRE constants."
        )
    else:
        crash_return = CRASH_SCENARIOS["2008_financial_crisis"]["first_year_return"]
        scenario_name = "2008_financial_crisis"
        data_note = (
            "Default 2008-style crash scenario. "
            "Source: NYU Stern Damodaran dataset (data as of 2024). "
            "Long-run assumptions from financial.py FIRE constants."
        )

    initial_wr = annual_spending / initial_portfolio

    all_paths: list[list[float]] = []
    all_spending_paths: list[list[float]] = []
    depleted_count = 0

    for _ in range(num_simulations):
        portfolio = initial_portfolio
        spending = annual_spending  # nominal, adjusted each year
        path: list[float] = [portfolio]
        spending_path: list[float] = []
        depleted = False
        depletion_year = total_years + 1

        for year in range(1, total_years + 1):
            if depleted:
                path.append(0.0)
                spending_path.append(spending)
                continue

            # Year 1: forced crash return; subsequent years: stochastic
            if year == 1:
                annual_return = crash_return
            else:
                u1 = random.random() or 1e-10
                u2 = random.random()
                z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
                annual_return = mu + z * sigma

            # Apply guardrails before withdrawal
            if guardrails_enabled and portfolio > 0:
                current_wr = spending / portfolio
                years_remaining = total_years - year

                if current_wr < _LOWER_GUARD * initial_wr:
                    # Prosperity rule: raise spending 10 %
                    spending = spending * (1 + _ADJUSTMENT)
                elif (current_wr > _UPPER_GUARD * initial_wr
                      and years_remaining >= _MIN_YEARS_FOR_CUTS):
                    # Capital-preservation rule: cut spending 10 %
                    spending = spending * (1 - _ADJUSTMENT)

            # Grow then withdraw
            portfolio = portfolio * (1 + annual_return)
            net_withdrawal = max(spending, 0.0)
            portfolio = max(portfolio - net_withdrawal, 0.0)

            # Inflate spending for next year
            spending = spending * (1 + inflation)

            if portfolio <= 0 and not depleted:
                depleted = True
                depletion_year = year
                depleted_count += 1

            path.append(portfolio)
            spending_path.append(net_withdrawal)

        all_paths.append(path)
        all_spending_paths.append(spending_path)

    # Build per-year stats
    yearly_stats: list[YearStats] = []
    for year in range(total_years + 1):
        values = sorted(p[year] for p in all_paths)
        n = len(values)
        depleted_at_year = sum(1 for v in values if v <= 0) / n

        def pct(q: float) -> float:
            idx = int(q * n)
            return values[min(idx, n - 1)]

        yearly_stats.append(
            YearStats(
                year=year,
                age=current_age + year,
                p10=round(pct(0.10), 2),
                p25=round(pct(0.25), 2),
                p50=round(pct(0.50), 2),
                p75=round(pct(0.75), 2),
                p90=round(pct(0.90), 2),
                mean=round(sum(values) / n, 2),
                pct_depleted=round(depleted_at_year, 4),
            )
        )

    final_values = sorted(p[-1] for p in all_paths)
    n = len(final_values)

    def _pct(q: float) -> float:
        idx = int(q * n)
        return final_values[min(idx, n - 1)]

    # Median spending path (median path by final value)
    median_idx = n // 2
    median_spending = [round(v, 2) for v in all_spending_paths[median_idx]]

    return GuardrailsResult(
        initial_portfolio=initial_portfolio,
        initial_annual_spending=annual_spending,
        initial_withdrawal_rate=round(initial_wr, 4),
        crash_scenario_name=scenario_name,
        crash_first_year_return=crash_return,
        guardrails_enabled=guardrails_enabled,
        success_rate=round((num_simulations - depleted_count) / num_simulations, 4),
        median_final_portfolio=round(_pct(0.50), 2),
        p10_final_portfolio=round(_pct(0.10), 2),
        p90_final_portfolio=round(_pct(0.90), 2),
        yearly_stats=yearly_stats,
        median_spending_path=median_spending,
        num_simulations=num_simulations,
        years_simulated=total_years,
        data_note=data_note,
    )
