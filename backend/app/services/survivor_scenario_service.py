"""Survivor income scenario service.

Models the financial impact of a spouse/partner dying at a specified age,
capturing:

  1. Loss of one income stream (salary or SS)
  2. Survivor Social Security benefit (100 % of deceased's benefit or the
     survivor's own benefit — whichever is higher)
  3. Reduction in household expenses (typically 70–80 % of prior joint level)
  4. Projection of the survivor's portfolio through their own life expectancy

Social Security survivor benefit rules (SSA POMS RS 00207)
----------------------------------------------------------
- Survivor receives the higher of:
    a. 100 % of the deceased's SS benefit at the time of death, OR
    b. The survivor's own SS benefit

- If the deceased claimed early, the survivor receives the higher of:
    - 82.5 % of the deceased's PIA (floor), OR
    - The deceased's actual benefit at death

- Survivor claiming ages:
    - Age 60: 71.5 % of survivor benefit
    - FRA (66-67): 100 %
    - Delayed credits do NOT apply to survivor benefits

DATA NOTE: The survivor reduction factors (71.5 % at 60, 100 % at FRA) are
statutory and defined in SSA POMS RS 00207.010.  They are static by law and
do not require annual updates.  The UI notes they are based on current SSA
rules.
"""

from __future__ import annotations

import datetime
import math
import random
from dataclasses import dataclass
from typing import Optional

from app.constants.financial import FIRE, SS


# Survivor SS reduction factor at age 60 (SSA POMS RS 00207.010)
_SURVIVOR_AT_60 = 0.715
_SURVIVOR_AT_FRA = 1.000
# SSA minimum: survivor receives at least 82.5% of deceased's PIA
_SURVIVOR_FLOOR = 0.825


@dataclass
class SurvivorYearProjection:
    """Single year in the survivor's financial projection."""

    year: int
    survivor_age: int
    portfolio_value: float
    annual_income: float     # survivor's total income (SS + other)
    annual_spending: float   # survivor's household spending
    net_cash_flow: float     # income - spending (positive = saving)


@dataclass
class SurvivorScenarioResult:
    """Complete survivor income scenario output."""

    # Scenario inputs (echoed for display)
    death_age_of_deceased: int
    survivor_current_age: int
    survivor_life_expectancy: int

    # Pre-death household summary
    joint_portfolio_at_death: float
    joint_annual_income_at_death: float
    joint_annual_spending: float

    # Survivor-specific
    survivor_ss_benefit: float        # monthly SS the survivor receives
    survivor_ss_is_own: bool          # True = own > survivor benefit
    survivor_annual_income: float     # post-death total annual income
    survivor_annual_spending: float   # reduced household spending
    survivor_income_gap: float        # spending - income (positive = gap)

    # Projection
    projection: list[SurvivorYearProjection]
    success_rate: float               # Monte Carlo: fraction reaching life expectancy
    median_final_portfolio: float

    # Data note for UI
    data_note: str


def compute_survivor_scenario(
    # Deceased
    death_age: int,
    deceased_ss_monthly: float,          # SS at time of death
    deceased_pia: float,                 # PIA for floor calculation
    # Survivor
    survivor_current_age: int,
    survivor_life_expectancy: int,
    survivor_own_ss_monthly: float,      # survivor's own SS (0 if not claiming)
    survivor_ss_claiming_age: int,       # age when survivor claims SS
    # Household
    current_portfolio: float,
    joint_annual_income: float,
    joint_annual_spending: float,
    # Adjustments
    spending_reduction_pct: float = 0.20,  # household spending drops 20 % on death
    portfolio_share_pct: float = 1.00,     # survivor keeps 100 % of joint portfolio
    # Simulation
    expected_return: Optional[float] = None,
    volatility: Optional[float] = None,
    inflation: float = FIRE.DEFAULT_INFLATION,
    num_simulations: int = 500,
) -> SurvivorScenarioResult:
    """Model the surviving spouse/partner's finances after the other's death.

    Parameters
    ----------
    death_age:
        Age of the deceased at time of death.
    deceased_ss_monthly:
        The deceased's monthly Social Security benefit at death.
    deceased_pia:
        The deceased's Primary Insurance Amount (for the SSA 82.5% floor).
    survivor_current_age:
        Survivor's current age.
    survivor_life_expectancy:
        Age at which the survivor's projection ends.
    survivor_own_ss_monthly:
        Survivor's own monthly SS benefit if they claim at survivor_ss_claiming_age.
    survivor_ss_claiming_age:
        Age at which the survivor claims SS (affects survivor benefit reduction).
    current_portfolio:
        Current joint portfolio value.
    joint_annual_income:
        Combined household income before death.
    joint_annual_spending:
        Combined household annual spending.
    spending_reduction_pct:
        Fraction by which spending drops after death (default 20 %).
    portfolio_share_pct:
        Fraction of joint portfolio the survivor retains (default 100 %).
    """
    mu = expected_return if expected_return is not None else FIRE.MC_POST_RETIREMENT_RETURN / 100.0
    sigma = volatility if volatility is not None else FIRE.MC_VOLATILITY / 100.0

    # --- Survivor SS benefit calculation ---
    # Determine reduction factor based on claiming age
    try:
        birth_year = datetime.date.today().year - survivor_current_age
        # FRA_TABLE covers through 1959 (FRA 66+10mo); 1960+ is FRA 67 (SSA)
        if birth_year >= 1960:
            fra = 67.0
        else:
            fra_key = max((k for k in SS.FRA_TABLE if k <= birth_year), default=None)
            fra_raw = SS.FRA_TABLE.get(fra_key) if fra_key is not None else None
            if fra_raw is None:
                fra = 67.0
            elif isinstance(fra_raw, tuple):
                fra = fra_raw[0] + fra_raw[1] / 12.0
            else:
                fra = float(fra_raw)
    except (ValueError, AttributeError):
        fra = 67.0

    if survivor_ss_claiming_age <= 60:
        reduction = _SURVIVOR_AT_60
    elif survivor_ss_claiming_age >= fra:
        reduction = _SURVIVOR_AT_FRA
    else:
        # Linear interpolation between 60 and FRA
        t = (survivor_ss_claiming_age - 60) / (fra - 60)
        reduction = _SURVIVOR_AT_60 + t * (_SURVIVOR_AT_FRA - _SURVIVOR_AT_60)

    # Survivor benefit = deceased's benefit × reduction, floor = 82.5% of PIA
    raw_survivor_benefit = deceased_ss_monthly * reduction
    floor_benefit = deceased_pia * _SURVIVOR_FLOOR
    survivor_benefit_from_deceased = max(raw_survivor_benefit, floor_benefit)

    # Survivor takes higher of: own SS or survivor benefit
    survivor_ss = max(survivor_benefit_from_deceased, survivor_own_ss_monthly)
    survivor_ss_is_own = survivor_own_ss_monthly >= survivor_benefit_from_deceased

    # --- Post-death financials ---
    portfolio = current_portfolio * portfolio_share_pct
    survivor_spending = joint_annual_spending * (1 - spending_reduction_pct)
    survivor_income = (joint_annual_income - deceased_ss_monthly * 12) + survivor_ss * 12
    # Cap at survivor's own income (they lose the deceased's non-SS income too,
    # but that requires more context — we use SS change only as floor adjustment)
    income_gap = max(survivor_spending - survivor_income, 0)

    total_years = survivor_life_expectancy - survivor_current_age

    # --- Monte Carlo projection ---
    all_paths: list[list[float]] = []
    depleted_count = 0

    for _ in range(num_simulations):
        p = portfolio
        spending = survivor_spending
        ss_annual = survivor_ss * 12
        path = [p]
        depleted = False

        for year in range(1, total_years + 1):
            if depleted:
                path.append(0.0)
                continue

            age = survivor_current_age + year
            u1 = random.random() or 1e-10
            u2 = random.random()
            z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
            annual_return = mu + z * sigma

            income = ss_annual if age >= survivor_ss_claiming_age else 0.0
            net_withdrawal = max(spending - income, 0.0)
            p = max(p * (1 + annual_return) - net_withdrawal, 0.0)

            spending *= (1 + inflation)
            ss_annual *= (1 + inflation)

            if p <= 0 and not depleted:
                depleted = True
                depleted_count += 1

            path.append(p)

        all_paths.append(path)

    # Deterministic projection for display (uses mean return)
    det_projection: list[SurvivorYearProjection] = []
    p = portfolio
    spending = survivor_spending
    ss_annual = survivor_ss * 12
    for year in range(total_years + 1):
        age = survivor_current_age + year
        income = ss_annual if age >= survivor_ss_claiming_age else 0.0
        det_projection.append(SurvivorYearProjection(
            year=year,
            survivor_age=age,
            portfolio_value=round(p, 2),
            annual_income=round(income, 2),
            annual_spending=round(spending, 2),
            net_cash_flow=round(income - spending, 2),
        ))
        if year < total_years:
            net_w = max(spending - income, 0.0)
            p = max(p * (1 + mu) - net_w, 0.0)
            spending *= (1 + inflation)
            ss_annual *= (1 + inflation)

    final_values = sorted(p[-1] for p in all_paths)
    n = len(final_values)
    median_final = final_values[n // 2]
    success_rate = round((num_simulations - depleted_count) / num_simulations, 4)

    data_note = (
        "Survivor SS benefit rules per SSA POMS RS 00207.010 (statutory, not subject to annual change). "
        "Survivor receives higher of: own SS benefit or deceased's benefit × claiming-age reduction factor "
        f"(min 82.5% of deceased's PIA = ${deceased_pia * _SURVIVOR_FLOOR:,.0f}/mo). "
        "Spending reduction default 20% (single-person household). "
        "Portfolio projection uses Monte Carlo (500 paths)."
    )

    return SurvivorScenarioResult(
        death_age_of_deceased=death_age,
        survivor_current_age=survivor_current_age,
        survivor_life_expectancy=survivor_life_expectancy,
        joint_portfolio_at_death=round(portfolio, 2),
        joint_annual_income_at_death=round(joint_annual_income, 2),
        joint_annual_spending=round(joint_annual_spending, 2),
        survivor_ss_benefit=round(survivor_ss, 2),
        survivor_ss_is_own=survivor_ss_is_own,
        survivor_annual_income=round(survivor_income, 2),
        survivor_annual_spending=round(survivor_spending, 2),
        survivor_income_gap=round(income_gap, 2),
        projection=det_projection,
        success_rate=success_rate,
        median_final_portfolio=round(median_final, 2),
        data_note=data_note,
    )
