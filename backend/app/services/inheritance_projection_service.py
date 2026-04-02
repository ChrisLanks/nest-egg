"""Multi-generational wealth and inheritance projection service.

Models what heirs receive under different spend-down strategies by projecting
the retiree's portfolio through their life expectancy and computing the
residual estate under several scenarios.

Spend-down strategies modelled
--------------------------------
1. **Fixed withdrawal** (4% rule / user-specified rate) — constant real
   spending, residual is what's left when the retiree dies.
2. **Minimum distribution only** — spend only RMDs + SS + pension; let the
   rest compound.  Maximises inheritance but may leave money on the table.
3. **Spend to zero** — target depleting the portfolio by life expectancy.
   Maximises retiree spending, leaves nothing (intentional).
4. **Legacy target** — reverse-engineer the annual withdrawal that leaves a
   specified dollar amount to heirs after inflation adjustment.

Estate and inheritance adjustments
------------------------------------
- Federal estate tax: applicable only above the exemption threshold.
  The exemption is sourced from the financial.py TAX class (ESTATE_TAX section
  if present) or from the static table below.  The UI flags when the value
  may be pre-sunset (the TCJA estate tax provisions sunset after 2025).
- State estate taxes: NOT modelled (vary by state; user is directed to a CPA).

DATA NOTE: The federal estate tax exemption figures are from IRS Rev. Proc.
and IRS.gov/estate-gift-tax.  They ARE subject to change (the TCJA exemption
sunsets after 2025 to ~$7M per person at 2017 levels, adjusted for inflation).
The static table below is the ONE place to update this.  The UI surfaces a
⚠ "Exemption may change after 2025 (TCJA sunset)" notice.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from app.constants.financial import ESTATE, FIRE

# ---------------------------------------------------------------------------
# Federal estate tax exemption (per individual)
# SOURCE: IRS Rev. Proc. (annual inflation adjustments)
# DATA NOTE: TCJA-enhanced exemption is scheduled to sunset after Dec 31, 2025,
# reverting to ~$7M (2017 base, inflation-adjusted) unless Congress acts.
# Update this table each November when IRS publishes new exemptions.
# ---------------------------------------------------------------------------
_ESTATE_TAX_RATE = float(ESTATE.FEDERAL_TAX_RATE)  # Top marginal rate above exemption (IRC §2001)
_TCJA_SUNSET_WARNING = (
    "⚠ Federal estate tax exemption TCJA provisions extended through "
    f"{ESTATE.TCJA_SUNSET_YEAR} by the One Big Beautiful Bill Act. "
    "Consult an estate attorney for planning beyond that date."
)


def _best_year_exemption(year: int) -> float:
    return float(ESTATE.FEDERAL_EXEMPTION)


@dataclass
class SpendDownScenario:
    """Single spend-down strategy projection."""

    strategy_name: str
    annual_withdrawal: float          # starting withdrawal (today's dollars)
    withdrawal_rate: float            # as % of initial portfolio
    final_portfolio: float            # at end of projection (nominal)
    final_portfolio_real: float       # inflation-adjusted to today's dollars
    estate_before_tax: float          # gross estate = final portfolio + other assets
    federal_estate_tax: float         # tax owed (0 if below exemption)
    net_to_heirs: float               # after federal estate tax
    years_projected: int
    depleted_at_year: Optional[int]   # None if portfolio never depletes
    annual_values: list[float]        # portfolio value each year (for chart)


@dataclass
class InheritanceProjectionResult:
    """Full multi-strategy inheritance projection."""

    initial_portfolio: float
    annual_income: float              # SS + pension (reduces portfolio draws)
    current_age: int
    life_expectancy: int

    scenarios: list[SpendDownScenario]  # one per strategy

    # Estate context
    estate_tax_exemption: float
    estate_tax_rate: float
    tcja_sunset_applies: bool         # True if projection extends past 2025

    data_note: str


def project_inheritance(
    initial_portfolio: float,
    annual_income: float,
    annual_spending: float,
    current_age: int,
    life_expectancy: int,
    other_assets: float = 0.0,         # real estate, business equity, etc.
    legacy_target: Optional[float] = None,  # for "legacy target" scenario
    expected_return: Optional[float] = None,
    inflation: float = FIRE.DEFAULT_INFLATION,
) -> InheritanceProjectionResult:
    """Project portfolio residual under four spend-down strategies.

    Parameters
    ----------
    initial_portfolio:
        Liquid investable portfolio at start.
    annual_income:
        Annual income from non-portfolio sources (SS, pension) in today's dollars.
    annual_spending:
        Annual household spending in today's dollars.
    current_age:
        Retiree's current age.
    life_expectancy:
        Age at end of projection.
    other_assets:
        Non-portfolio assets (home equity, etc.) included in gross estate.
    legacy_target:
        Desired estate value in today's dollars for the "legacy target" scenario.
    expected_return:
        Annual nominal return (decimal). Defaults to FIRE.MC_POST_RETIREMENT_RETURN.
    inflation:
        Annual inflation rate.
    """
    if life_expectancy <= current_age:
        raise ValueError("life_expectancy must be greater than current_age")

    mu = expected_return if expected_return is not None else FIRE.MC_POST_RETIREMENT_RETURN / 100.0
    years = life_expectancy - current_age
    today_year = datetime.date.today().year
    end_year = today_year + years

    exemption = _best_year_exemption(today_year)
    tcja_sunset = end_year > ESTATE.TCJA_SUNSET_YEAR

    def _project(annual_withdrawal: float) -> SpendDownScenario:
        raise NotImplementedError  # placeholder; defined inline below

    def _run(
        strategy_name: str,
        annual_withdrawal: float,
    ) -> SpendDownScenario:
        p = initial_portfolio
        withdrawal = annual_withdrawal
        values = [p]
        depleted_at = None

        for yr in range(1, years + 1):
            income = annual_income * ((1 + inflation) ** yr)
            w = max(withdrawal * ((1 + inflation) ** yr) - income, 0.0)
            p = p * (1 + mu) - w
            if p <= 0 and depleted_at is None:
                depleted_at = yr
                p = 0.0
            values.append(round(p, 2))

        wr = annual_withdrawal / initial_portfolio if initial_portfolio > 0 else 0.0
        final_real = p / ((1 + inflation) ** years)
        gross_estate = p + other_assets
        tax = max((gross_estate - exemption) * _ESTATE_TAX_RATE, 0.0)
        net = max(gross_estate - tax, 0.0)

        return SpendDownScenario(
            strategy_name=strategy_name,
            annual_withdrawal=round(annual_withdrawal, 2),
            withdrawal_rate=round(wr, 4),
            final_portfolio=round(p, 2),
            final_portfolio_real=round(final_real, 2),
            estate_before_tax=round(gross_estate, 2),
            federal_estate_tax=round(tax, 2),
            net_to_heirs=round(net, 2),
            years_projected=years,
            depleted_at_year=depleted_at,
            annual_values=values,
        )

    # 1. Fixed 4% withdrawal
    scenario_4pct = _run(
        "4% Rule (fixed real spending)",
        annual_withdrawal=initial_portfolio * FIRE.DEFAULT_WITHDRAWAL_RATE,
    )

    # 2. Minimum — spend only what's needed beyond income (floor = 0 from portfolio)
    min_withdrawal = max(annual_spending - annual_income, 0.0)
    scenario_min = _run(
        "Minimum (spend down from income only)",
        annual_withdrawal=min_withdrawal,
    )

    # 3. Spend to zero — find withdrawal that depletes portfolio at life_expectancy
    # Solve: PV of withdrawal annuity = initial_portfolio
    # P * [(1-(1+r)^-n) / r] = portfolio (where r = real return = mu - inflation)
    real_r = (1 + mu) / (1 + inflation) - 1
    if abs(real_r) < 1e-9:
        stz_w = initial_portfolio / years if years > 0 else initial_portfolio
    else:
        annuity_factor = (1 - (1 + real_r) ** -years) / real_r if real_r != 0 else years
        net_needed = max(annual_spending - annual_income, 0.0)
        # If existing income covers spending, spend-to-zero means just spending the portfolio anyway
        # Withdrawal = (portfolio / annuity_factor) but we want the full spending
        stz_w = max(initial_portfolio / annuity_factor, net_needed)

    scenario_stz = _run(
        "Spend to Zero (maximise spending, zero estate)",
        annual_withdrawal=stz_w,
    )

    # 4. Legacy target
    if legacy_target is not None and legacy_target > 0:
        # Solve for withdrawal such that final portfolio = legacy_target (nominal)
        # FV(portfolio, r, n) - FV(withdrawal_stream, r, n) = legacy (nominal)
        # portfolio*(1+mu)^n - w * [(1+mu)^n - 1]/mu = legacy_nominal
        legacy_nominal = legacy_target * ((1 + inflation) ** years)
        if abs(mu) < 1e-9:
            legacy_w = max((initial_portfolio - legacy_target) / years, 0.0)
        else:
            fv_factor = ((1 + mu) ** years - 1) / mu
            portfolio_fv = initial_portfolio * (1 + mu) ** years
            legacy_w = max((portfolio_fv - legacy_nominal) / fv_factor, 0.0)
        # Net of income
        legacy_w_net = max(legacy_w - annual_income, 0.0)
        scenario_legacy = _run(
            f"Legacy Target (${legacy_target:,.0f} to heirs in today's dollars)",
            annual_withdrawal=legacy_w_net + annual_income,
        )
    else:
        scenario_legacy = _run(
            "Legacy Target (not specified — using 4% rule)",
            annual_withdrawal=initial_portfolio * FIRE.DEFAULT_WITHDRAWAL_RATE,
        )

    data_note = (
        f"Federal estate tax exemption: ${exemption:,.0f}/individual (tax year {today_year}). "
        f"Top estate tax rate: {_ESTATE_TAX_RATE*100:.0f}%. "
        + (_TCJA_SUNSET_WARNING if tcja_sunset else "")
        + " State estate taxes not modelled. "
        "Portfolio return and inflation from financial.py FIRE constants."
    )

    return InheritanceProjectionResult(
        initial_portfolio=initial_portfolio,
        annual_income=annual_income,
        current_age=current_age,
        life_expectancy=life_expectancy,
        scenarios=[scenario_4pct, scenario_min, scenario_stz, scenario_legacy],
        estate_tax_exemption=exemption,
        estate_tax_rate=_ESTATE_TAX_RATE,
        tcja_sunset_applies=tcja_sunset,
        data_note=data_note,
    )
