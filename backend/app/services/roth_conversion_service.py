"""Roth Conversion Optimizer service.

Calculates the tax-optimal annual Roth conversion amount by modelling
the interaction between income tax brackets, IRMAA Medicare surcharges,
and Required Minimum Distributions (RMDs).

Algorithm overview
------------------
For each projected year:
  1. Determine current income tax bracket from filing status + income.
  2. Calculate headroom to the *next* bracket ceiling.
  3. Cap conversion so projected income + conversion never crosses:
       a) the next income-tax bracket,
       b) an IRMAA tier boundary (for users >= 60).
  4. Convert the minimum of (headroom, remaining traditional balance).
  5. Grow both balances at the expected return rate.
  6. From age 73 onwards layer in RMDs (no conversion needed once RMDs
     exceed the bracket headroom).

The service is pure Python / no database — all inputs are passed in.
This makes it straightforward to unit-test and call from API endpoints
that have already fetched balances.

All dollar amounts are rounded to two decimal places in output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.constants.financial import MEDICARE, RMD, TAX

logger = logging.getLogger(__name__)

# ── Tax bracket helpers ────────────────────────────────────────────────────

# 2026 ordinary income brackets (rate, single ceiling, married ceiling)
# Using only the thresholds we need: top of each bracket.
# Source: IRS Rev. Proc. 2025-32
_BRACKETS_SINGLE = [
    (0.10, 11_925),
    (0.12, 48_475),
    (0.22, 103_350),
    (0.24, 197_300),
    (0.32, 250_525),
    (0.35, 626_350),
    (0.37, float("inf")),
]
_BRACKETS_MARRIED = [
    (0.10, 23_850),
    (0.12, 96_950),
    (0.22, 206_700),
    (0.24, 394_600),
    (0.32, 501_050),
    (0.35, 751_600),
    (0.37, float("inf")),
]

# Annual inflation adjustment applied to bracket ceilings
_BRACKET_COLA = 0.025


def _get_brackets(filing_status: str, years_from_now: int) -> list[tuple[float, float]]:
    """Return inflation-adjusted brackets for *years_from_now* in the future."""
    base = _BRACKETS_SINGLE if filing_status == "single" else _BRACKETS_MARRIED
    factor = (1 + _BRACKET_COLA) ** years_from_now
    return [(rate, ceil * factor) for rate, ceil in base]


def _marginal_rate(taxable_income: float, brackets: list[tuple[float, float]]) -> float:
    """Return the marginal tax rate for the given taxable income."""
    for rate, ceiling in brackets:
        if taxable_income <= ceiling:
            return rate
    return brackets[-1][0]


def _bracket_headroom(taxable_income: float, brackets: list[tuple[float, float]]) -> float:
    """Return dollars available before crossing into the next bracket."""
    for _, ceiling in brackets:
        if taxable_income < ceiling:
            return ceiling - taxable_income
    return 0.0


def _standard_deduction(filing_status: str, years_from_now: int) -> float:
    """Inflation-adjusted standard deduction."""
    base = (
        TAX.STANDARD_DEDUCTION_SINGLE
        if filing_status == "single"
        else TAX.STANDARD_DEDUCTION_MARRIED
    )
    return float(base) * (1 + _BRACKET_COLA) ** years_from_now


def _irmaa_headroom(magi: float, years_from_now: int) -> float:
    """Return dollars before the next IRMAA tier, or float('inf') if already at top."""
    # Project IRMAA thresholds forward (CPI ~3 %)
    brackets = MEDICARE.IRMAA_BRACKETS_SINGLE
    cola = 0.03
    for threshold, _, _ in brackets:
        if threshold == float("inf"):
            return float("inf")
        projected_threshold = float(threshold) * (1 + cola) ** years_from_now
        gap = projected_threshold - magi
        if gap > 0:
            return gap
    return float("inf")


def _rmd_amount(traditional_balance: float, age: int) -> float:
    """Calculate RMD for the given age and balance. Returns 0 before age 73."""
    if age < RMD.TRIGGER_AGE:
        return 0.0
    factor = float(RMD.UNIFORM_LIFETIME_TABLE.get(min(age, 120), 3.1))
    return traditional_balance / factor


# ── Data classes ───────────────────────────────────────────────────────────


@dataclass
class RothConversionInput:
    """Inputs for the Roth conversion optimizer."""

    traditional_balance: float
    """Current total balance in pre-tax (Traditional IRA / 401k) accounts."""

    roth_balance: float
    """Current total balance in Roth accounts."""

    current_income: float
    """Gross earned + passive income *excluding* any conversion amount."""

    current_age: int
    """User's current age in whole years."""

    filing_status: str = "single"
    """'single' or 'married'."""

    expected_return: float = 0.07
    """Expected annual nominal return (7 % default)."""

    years_to_project: int = 20
    """Number of years to model."""

    target_bracket_rate: Optional[float] = None
    """
    Convert up to (but not into) this bracket.
    None = use the bracket the user is currently in as the cap.
    """

    respect_irmaa: bool = True
    """When True, cap conversions to avoid crossing IRMAA tier boundaries."""


@dataclass
class RothConversionYear:
    """Single-year output from the Roth conversion optimizer."""

    year: int
    age: int
    optimal_conversion: float
    marginal_rate_at_conversion: float
    rmd_amount: float
    traditional_balance_start: float
    roth_balance_start: float
    traditional_balance_end: float
    roth_balance_end: float
    tax_cost_of_conversion: float
    notes: list[str] = field(default_factory=list)


@dataclass
class RothConversionResult:
    """Full multi-year Roth conversion plan."""

    years: list[RothConversionYear]
    total_converted: float
    total_tax_cost: float
    # Scenario: no conversions at all
    no_conversion_traditional_end: float
    no_conversion_roth_end: float
    # Scenario: with optimised conversions
    with_conversion_traditional_end: float
    with_conversion_roth_end: float
    # Rough estimate of lifetime tax saved
    estimated_tax_savings: float
    summary: str


# ── Service ────────────────────────────────────────────────────────────────


class RothConversionService:
    """
    Pure-Python Roth conversion optimizer.  No database access required.

    Usage::

        svc = RothConversionService()
        result = svc.optimize(
            RothConversionInput(
                traditional_balance=500_000,
                roth_balance=50_000,
                current_income=80_000,
                current_age=55,
                filing_status="single",
                years_to_project=20,
            )
        )
        for yr in result.years:
            print(yr.year, yr.optimal_conversion, yr.rmd_amount)
    """

    def optimize(self, inp: RothConversionInput) -> RothConversionResult:
        """
        Run the multi-year Roth conversion optimisation.

        Returns a :class:`RothConversionResult` with per-year detail and
        top-level summary statistics.
        """
        years: list[RothConversionYear] = []
        trad = inp.traditional_balance
        roth = inp.roth_balance
        total_converted = 0.0
        total_tax_cost = 0.0

        # Determine bracket cap (default: stay in current bracket)
        year0_brackets = _get_brackets(inp.filing_status, 0)
        std_ded_0 = _standard_deduction(inp.filing_status, 0)
        taxable_0 = max(0.0, inp.current_income - std_ded_0)
        current_rate = _marginal_rate(taxable_0, year0_brackets)
        bracket_cap_rate = inp.target_bracket_rate or current_rate

        for i in range(inp.years_to_project):
            year_num = i + 1
            age = inp.current_age + i
            notes: list[str] = []

            brackets = _get_brackets(inp.filing_status, i)
            std_ded = _standard_deduction(inp.filing_status, i)
            taxable_income = max(0.0, inp.current_income - std_ded)

            # RMD calculation (age at START of projection year)
            rmd = _rmd_amount(trad, age)
            if rmd > 0:
                notes.append(f"RMD of ${rmd:,.0f} required at age {age}")

            # Available headroom in bracket before cap rate
            headroom = 0.0
            running_income = taxable_income + rmd  # RMDs count as income
            for rate, ceiling in brackets:
                if running_income < ceiling and rate <= bracket_cap_rate:
                    headroom = ceiling - running_income
                    break

            # IRMAA cap
            if inp.respect_irmaa and age >= 55:
                magi = inp.current_income + rmd  # before conversion
                irmaa_room = _irmaa_headroom(magi, i)
                if irmaa_room < headroom:
                    headroom = irmaa_room
                    notes.append("Capped by IRMAA boundary")

            # Optimal conversion = min(headroom, remaining trad balance - rmd)
            available_trad = max(0.0, trad - rmd)
            conversion = round(min(headroom, available_trad), 2)
            if conversion < 0:
                conversion = 0.0

            rate_at_conversion = _marginal_rate(taxable_income + rmd + conversion, brackets)
            tax_cost = round(conversion * rate_at_conversion, 2)

            trad_end = round((trad - rmd - conversion) * (1 + inp.expected_return), 2)
            roth_end = round((roth + conversion) * (1 + inp.expected_return), 2)

            years.append(
                RothConversionYear(
                    year=year_num,
                    age=age,
                    optimal_conversion=conversion,
                    marginal_rate_at_conversion=rate_at_conversion,
                    rmd_amount=round(rmd, 2),
                    traditional_balance_start=round(trad, 2),
                    roth_balance_start=round(roth, 2),
                    traditional_balance_end=trad_end,
                    roth_balance_end=roth_end,
                    tax_cost_of_conversion=tax_cost,
                    notes=notes,
                )
            )

            total_converted += conversion
            total_tax_cost += tax_cost
            trad = trad_end
            roth = roth_end

        # Build no-conversion baseline for comparison
        nc_trad = inp.traditional_balance * (1 + inp.expected_return) ** inp.years_to_project
        nc_roth = inp.roth_balance * (1 + inp.expected_return) ** inp.years_to_project

        # Tax savings estimate: Roth withdrawals are tax-free;
        # traditional withdrawals at estimated 22 % marginal rate
        converted_after_growth = total_converted * (
            (1 + inp.expected_return) ** (inp.years_to_project / 2)
        )
        tax_savings = max(0.0, converted_after_growth * 0.22 - total_tax_cost)

        if total_converted > 0:
            summary = (
                f"Converting ${total_converted:,.0f} over {inp.years_to_project} years "
                f"(tax cost ${total_tax_cost:,.0f}) may save ~${tax_savings:,.0f} "
                f"in future taxes. Traditional balance shrinks from "
                f"${inp.traditional_balance:,.0f} to ${trad:,.0f}; "
                f"Roth grows from ${inp.roth_balance:,.0f} to ${roth:,.0f}."
            )
        else:
            summary = (
                "No conversions recommended — current income already fills the target "
                "tax bracket, or traditional balance is fully covered by RMDs."
            )

        return RothConversionResult(
            years=years,
            total_converted=round(total_converted, 2),
            total_tax_cost=round(total_tax_cost, 2),
            no_conversion_traditional_end=round(nc_trad, 2),
            no_conversion_roth_end=round(nc_roth, 2),
            with_conversion_traditional_end=round(trad, 2),
            with_conversion_roth_end=round(roth, 2),
            estimated_tax_savings=round(tax_savings, 2),
            summary=summary,
        )
