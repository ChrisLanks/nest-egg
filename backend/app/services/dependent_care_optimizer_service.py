"""Dependent care FSA and childcare cost optimizer.

Computes the optimal split between the Dependent Care FSA (DC-FSA) and the
Child and Dependent Care Tax Credit (CDCTC) to maximise after-tax benefit.

The two benefits:
  1. DC-FSA: Pre-tax salary reduction; saves FICA (7.65%) + marginal income
     tax on contributed dollars.  Annual contribution limit = $5,000 per
     household (or $2,500 if married filing separately).
     Source: IRS Publication 503 / IRC §129.

  2. CDCTC (Form 2441): A non-refundable credit on up to $3,000 of expenses
     per dependent (max 2 dependents = $6,000).  Credit rate is 20–35%
     depending on AGI.  Expenses claimed for the credit must be REDUCED by
     any DC-FSA contributions (they cannot double-count the same dollars).

The optimizer:
  - Models both benefits independently and as a combined strategy.
  - DC-FSA always wins for households in the 22%+ bracket because FICA
    savings alone (7.65%) make it superior to the credit rate for those
    dollars.  But the credit can still apply to remaining eligible expenses.

DATA NOTE: Contribution limits and credit rates are from IRS Publication 503
and IRC §129.  These are updated by the IRS annually (typically in Rev. Proc.
each November).  The static tables below have a YEAR column so stale data is
detectable.  When the IRS publishes new limits, add a row to the appropriate
dict.  The UI displays "Based on IRS Publication 503 (tax year YYYY)" with
a note that it may not reflect the most current limits.

Relevant IRS resources (no scraping needed — limits rarely change):
  https://www.irs.gov/publications/p503
  https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-YYYY
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Static IRS data
# DATA NOTE: Update when IRS publishes new limits (usually November for
# following tax year).  Source: IRS Publication 503 / Rev. Proc. annually.
# ---------------------------------------------------------------------------

# DC-FSA annual contribution limit (per household / MFJ)
# IRC §129(a)(2)(B): $5,000 per household; $2,500 MFS
_DCFSA_LIMIT_BY_YEAR: dict[int, float] = {
    2022: 5_000,
    2023: 5_000,
    2024: 5_000,
    2025: 5_000,  # unchanged; update if IRS revises
    2026: 5_000,  # unchanged; update if IRS revises
}

# CDCTC eligible expense cap (Form 2441)
_CDCTC_EXPENSE_CAP_BY_YEAR: dict[int, dict] = {
    2022: {"one_dependent": 3_000, "two_or_more": 6_000},
    2023: {"one_dependent": 3_000, "two_or_more": 6_000},
    2024: {"one_dependent": 3_000, "two_or_more": 6_000},
    2025: {"one_dependent": 3_000, "two_or_more": 6_000},
    2026: {"one_dependent": 3_000, "two_or_more": 6_000},
}

# CDCTC credit rate by AGI (rate applies to eligible expenses)
# IRC §21(a)(2); rate phases down from 35% to 20% as AGI rises above $15k
_CDCTC_RATE_SCHEDULE: list[tuple[float, float]] = [
    (15_000, 0.35),
    (17_000, 0.34),
    (19_000, 0.33),
    (21_000, 0.32),
    (23_000, 0.31),
    (25_000, 0.30),
    (27_000, 0.29),
    (29_000, 0.28),
    (31_000, 0.27),
    (33_000, 0.26),
    (35_000, 0.25),
    (37_000, 0.24),
    (39_000, 0.23),
    (41_000, 0.22),
    (43_000, 0.21),
    (float("inf"), 0.20),  # AGI > $43,000: 20% flat
]

# FICA employee rate (Social Security 6.2% + Medicare 1.45%)
_FICA_RATE = 0.0765  # unchanged by law until Social Security wage base adjustments

_DATA_NOTE = (
    "Based on IRS Publication 503 and IRC §129 / §21. "
    "DC-FSA limit: $5,000/household (unchanged 2022–2025). "
    "CDCTC expense caps: $3,000 (1 dependent) / $6,000 (2+). "
    "⚠ Verify against the most current IRS guidance at irs.gov/publications/p503."
)


def _best_year_value(table: dict, year: int):
    y = max((k for k in table if k <= year), default=min(table))
    return table[y]


def _cdctc_rate(agi: float) -> float:
    """Determine CDCTC credit rate from AGI per IRS Phase-down table."""
    for threshold, rate in _CDCTC_RATE_SCHEDULE:
        if agi <= threshold:
            return rate
    return 0.20


@dataclass
class DependentCareOptimizationResult:
    """Output of the DC-FSA + CDCTC optimization."""

    tax_year: int

    # Inputs echoed
    annual_childcare_expenses: float
    num_dependents: int
    agi: float
    marginal_rate: float
    filing_status: str  # "mfj" | "mfs" | "single" | "hoh"

    # DC-FSA analysis
    dcfsa_contribution: float        # recommended contribution
    dcfsa_tax_savings: float         # income tax + FICA saved
    dcfsa_limit: float

    # CDCTC analysis
    cdctc_eligible_expenses: float   # after subtracting DC-FSA contribution
    cdctc_rate: float
    cdctc_credit: float              # non-refundable credit amount

    # Combined result
    total_benefit: float             # FSA savings + credit
    effective_childcare_cost: float  # expenses - total_benefit
    effective_cost_pct: float        # effective cost / gross expenses

    # Comparison: credit-only vs FSA-only vs combined
    credit_only_benefit: float
    fsa_only_benefit: float
    combined_benefit: float          # == total_benefit

    recommendation: str
    data_note: str


def optimize_dependent_care(
    annual_childcare_expenses: float,
    num_dependents: int,
    agi: float,
    marginal_rate: float,
    filing_status: str = "mfj",
    tax_year: Optional[int] = None,
) -> DependentCareOptimizationResult:
    """Compute optimal DC-FSA + CDCTC strategy.

    Parameters
    ----------
    annual_childcare_expenses:
        Total annual qualified dependent care expenses.
    num_dependents:
        Number of qualifying children/dependents (caps at 2 for CDCTC).
    agi:
        Adjusted gross income (before DC-FSA pre-tax reduction).
    marginal_rate:
        Federal marginal income tax rate as decimal (e.g. 0.22).
    filing_status:
        "mfj" | "mfs" | "single" | "hoh".
    tax_year:
        Tax year (defaults to current year).
    """
    year = tax_year or datetime.date.today().year

    dcfsa_limit = _best_year_value(_DCFSA_LIMIT_BY_YEAR, year)
    if filing_status == "mfs":
        dcfsa_limit = dcfsa_limit / 2  # $2,500 for MFS

    expense_caps = _best_year_value(_CDCTC_EXPENSE_CAP_BY_YEAR, year)
    cdctc_cap = expense_caps["two_or_more"] if num_dependents >= 2 else expense_caps["one_dependent"]

    # ---- DC-FSA ----
    dcfsa_contribution = min(annual_childcare_expenses, dcfsa_limit)
    # Tax savings = pre-tax dollars × (marginal rate + FICA)
    dcfsa_tax_savings = round(dcfsa_contribution * (marginal_rate + _FICA_RATE), 2)

    # ---- CDCTC (expenses must be reduced by DC-FSA contribution) ----
    credit_eligible = max(min(annual_childcare_expenses, cdctc_cap) - dcfsa_contribution, 0)
    cdctc_rate = _cdctc_rate(agi)
    cdctc_credit = round(credit_eligible * cdctc_rate, 2)

    total_benefit = round(dcfsa_tax_savings + cdctc_credit, 2)
    effective_cost = round(annual_childcare_expenses - total_benefit, 2)
    effective_pct = round(effective_cost / annual_childcare_expenses, 4) if annual_childcare_expenses > 0 else 0.0

    # ---- Comparison strategies ----
    # Credit-only: no FSA, full expenses go to credit (capped)
    credit_only_eligible = min(annual_childcare_expenses, cdctc_cap)
    credit_only = round(credit_only_eligible * cdctc_rate, 2)

    # FSA-only: max FSA, no additional credit (credit_eligible = 0)
    fsa_only = dcfsa_tax_savings  # same as dcfsa_tax_savings (no credit)

    # Recommendation
    if total_benefit >= max(credit_only, fsa_only):
        rec = (
            f"Combined strategy: contribute ${dcfsa_contribution:,.0f} to DC-FSA "
            f"(saving ${dcfsa_tax_savings:,.0f} in taxes) and claim the CDCTC "
            f"on the remaining ${credit_eligible:,.0f} "
            f"(credit: ${cdctc_credit:,.0f}). "
            f"Total benefit: ${total_benefit:,.0f}."
        )
    elif credit_only >= fsa_only:
        rec = (
            f"Credit-only strategy yields ${credit_only:,.0f} — more than the FSA "
            f"alone (${fsa_only:,.0f}).  Check if your employer offers DC-FSA; "
            "if so, the combined strategy is typically better."
        )
    else:
        rec = (
            f"DC-FSA alone (${fsa_only:,.0f}) beats the credit-only strategy "
            f"(${credit_only:,.0f}) at your marginal rate ({marginal_rate*100:.0f}%)."
        )

    return DependentCareOptimizationResult(
        tax_year=year,
        annual_childcare_expenses=annual_childcare_expenses,
        num_dependents=num_dependents,
        agi=agi,
        marginal_rate=marginal_rate,
        filing_status=filing_status,
        dcfsa_contribution=dcfsa_contribution,
        dcfsa_tax_savings=dcfsa_tax_savings,
        dcfsa_limit=dcfsa_limit,
        cdctc_eligible_expenses=credit_eligible,
        cdctc_rate=cdctc_rate,
        cdctc_credit=cdctc_credit,
        total_benefit=total_benefit,
        effective_childcare_cost=effective_cost,
        effective_cost_pct=effective_pct,
        credit_only_benefit=credit_only,
        fsa_only_benefit=fsa_only,
        combined_benefit=total_benefit,
        recommendation=rec,
        data_note=_DATA_NOTE,
    )
