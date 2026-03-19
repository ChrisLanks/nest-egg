"""Mortgage analyzer and refinance comparison service.

Pure-Python / no database — all inputs passed in from the API layer which
fetches the mortgage account data.

Features
--------
- Full amortization schedule for current loan
- Refinance scenario: new rate/term → new schedule
- Side-by-side comparison: total interest, monthly savings, break-even point
- Extra payment impact: how much early payoff + interest saved
- Equity projection over time
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


# ── Data classes ───────────────────────────────────────────────────────────


@dataclass
class AmortizationRow:
    """Single month in an amortization schedule."""

    month: int
    payment: float
    principal: float
    interest: float
    balance: float
    cumulative_interest: float


@dataclass
class LoanSummary:
    """High-level summary for a loan scenario."""

    monthly_payment: float
    total_paid: float
    total_interest: float
    total_principal: float
    payoff_months: int
    payoff_date: str  # ISO date string


@dataclass
class RefinanceComparison:
    """Side-by-side comparison of current loan vs refinance scenario."""

    current: LoanSummary
    refinanced: LoanSummary
    monthly_savings: float
    lifetime_interest_savings: float
    break_even_months: int  # months until cumulative savings > closing costs
    break_even_date: str  # ISO date when break-even is reached
    recommendation: str


@dataclass
class ExtraPaymentImpact:
    """Impact of making regular extra principal payments."""

    original_payoff_months: int
    new_payoff_months: int
    months_saved: int
    interest_saved: float
    original_total_interest: float
    new_total_interest: float


@dataclass
class MortgageAnalysis:
    """Complete mortgage analysis result."""

    loan_balance: float
    interest_rate: float  # annual, as decimal (e.g. 0.065)
    monthly_payment: float
    remaining_months: int
    amortization: list[AmortizationRow]
    summary: LoanSummary
    refinance: Optional[RefinanceComparison]
    extra_payment: Optional[ExtraPaymentImpact]
    equity_milestones: list[dict]  # [{pct: 20, month: N, date: "YYYY-MM"}]


# ── Core math ──────────────────────────────────────────────────────────────


def _monthly_payment(principal: float, annual_rate: float, months: int) -> float:
    """Standard mortgage payment formula (fixed rate)."""
    if principal <= 0 or months <= 0:
        return 0.0
    if annual_rate == 0:
        return round(principal / months, 2)
    r = annual_rate / 12
    pmt = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)
    return round(pmt, 2)


def _amortize(
    balance: float,
    annual_rate: float,
    monthly_payment: float,
    max_months: int = 480,
    extra_monthly: float = 0.0,
) -> list[AmortizationRow]:
    """Build full amortization schedule."""
    rows: list[AmortizationRow] = []
    r = annual_rate / 12
    cumulative_interest = 0.0

    for m in range(1, max_months + 1):
        if balance <= 0:
            break
        interest = round(balance * r, 2)
        pmt = min(monthly_payment + extra_monthly, balance + interest)
        principal = round(pmt - interest, 2)
        balance = round(max(0.0, balance - principal), 2)
        cumulative_interest = round(cumulative_interest + interest, 2)
        rows.append(
            AmortizationRow(
                month=m,
                payment=round(pmt, 2),
                principal=principal,
                interest=interest,
                balance=balance,
                cumulative_interest=cumulative_interest,
            )
        )
        if balance == 0:
            break

    return rows


def _iso_month(start: date, months_ahead: int) -> str:
    """Return ISO YYYY-MM string for a date offset by months_ahead months."""
    year = start.year + (start.month - 1 + months_ahead) // 12
    month = (start.month - 1 + months_ahead) % 12 + 1
    return f"{year:04d}-{month:02d}"


def _summarise(rows: list[AmortizationRow], today: date) -> LoanSummary:
    if not rows:
        return LoanSummary(0, 0, 0, 0, 0, today.isoformat())
    total_interest = rows[-1].cumulative_interest
    total_paid = sum(r.payment for r in rows)
    total_principal = total_paid - total_interest
    n = len(rows)
    payoff_date = _iso_month(today, n)
    return LoanSummary(
        monthly_payment=rows[0].payment,
        total_paid=round(total_paid, 2),
        total_interest=round(total_interest, 2),
        total_principal=round(total_principal, 2),
        payoff_months=n,
        payoff_date=payoff_date,
    )


def _equity_milestones(
    original_balance: float,
    rows: list[AmortizationRow],
    today: date,
    thresholds: tuple[float, ...] = (0.20, 0.50, 0.80, 1.0),
) -> list[dict]:
    """Return months/dates when equity crosses each threshold."""
    milestones = []
    for pct in thresholds:
        target_remaining = original_balance * (1 - pct)
        for row in rows:
            if row.balance <= target_remaining:
                milestones.append(
                    {
                        "equity_pct": int(pct * 100),
                        "month": row.month,
                        "date": _iso_month(today, row.month),
                        "balance_at_milestone": row.balance,
                    }
                )
                break
    return milestones


# ── Service ────────────────────────────────────────────────────────────────


class MortgageAnalyzerService:
    """
    Analyses a mortgage loan and optionally models a refinance scenario.

    All methods are static — no database access.

    Usage::

        result = MortgageAnalyzerService.analyze(
            current_balance=350_000,
            annual_rate=0.065,
            remaining_months=300,
            refinance_rate=0.055,
            refinance_term_months=360,
            closing_costs=5_000,
            extra_monthly_payment=200,
        )
    """

    @staticmethod
    def analyze(
        current_balance: float,
        annual_rate: float,
        remaining_months: int,
        refinance_rate: Optional[float] = None,
        refinance_term_months: Optional[int] = None,
        closing_costs: float = 0.0,
        extra_monthly_payment: float = 0.0,
        today: Optional[date] = None,
    ) -> MortgageAnalysis:
        """
        Full mortgage analysis.

        Parameters
        ----------
        current_balance:
            Remaining principal balance.
        annual_rate:
            Current annual interest rate as a decimal (e.g. 0.065 for 6.5%).
        remaining_months:
            Months remaining on current loan.
        refinance_rate:
            New annual rate if refinancing (optional).
        refinance_term_months:
            New term in months if refinancing (optional, defaults to remaining_months).
        closing_costs:
            Up-front cost to refinance; used in break-even calculation.
        extra_monthly_payment:
            Additional principal payment each month on current loan.
        today:
            Reference date (defaults to current date).
        """
        if today is None:
            today = date.today()

        balance = max(0.0, current_balance)
        rate = max(0.0, annual_rate)
        months = max(1, remaining_months)

        # Current loan amortization
        pmt = _monthly_payment(balance, rate, months)
        rows = _amortize(balance, rate, pmt, extra_monthly=extra_monthly_payment)
        summary = _summarise(rows, today)

        # Extra payment impact (compared to baseline with no extra)
        extra_impact: Optional[ExtraPaymentImpact] = None
        if extra_monthly_payment > 0:
            baseline_rows = _amortize(balance, rate, pmt, extra_monthly=0.0)
            extra_impact = ExtraPaymentImpact(
                original_payoff_months=len(baseline_rows),
                new_payoff_months=len(rows),
                months_saved=len(baseline_rows) - len(rows),
                interest_saved=round(
                    baseline_rows[-1].cumulative_interest - rows[-1].cumulative_interest,
                    2,
                ),
                original_total_interest=round(baseline_rows[-1].cumulative_interest, 2),
                new_total_interest=round(rows[-1].cumulative_interest, 2),
            )

        # Refinance comparison
        refi: Optional[RefinanceComparison] = None
        if refinance_rate is not None and refinance_rate > 0:
            refi_months = refinance_term_months or months
            refi_pmt = _monthly_payment(balance, refinance_rate, refi_months)
            refi_rows = _amortize(balance, refinance_rate, refi_pmt)
            refi_summary = _summarise(refi_rows, today)

            monthly_savings = round(pmt - refi_pmt, 2)
            interest_savings = round(summary.total_interest - refi_summary.total_interest, 2)

            # Break-even: month when cumulative savings first exceed closing costs
            break_even = 0
            if monthly_savings > 0 and closing_costs >= 0:
                break_even = (
                    int(closing_costs / monthly_savings) + 1 if monthly_savings > 0 else 9999
                )

            if monthly_savings > 0:
                rec = (
                    f"Refinancing to {refinance_rate * 100:.2f}% saves "
                    f"${monthly_savings:,.0f}/month. "
                    f"Break-even in {break_even} months "
                    f"({_iso_month(today, break_even)}). "
                    f"Total interest savings: ${interest_savings:,.0f}."
                )
            elif monthly_savings < 0:
                rec = (
                    f"The new rate ({refinance_rate * 100:.2f}%) is higher — "
                    f"refinancing would cost ${abs(monthly_savings):,.0f} more/month. "
                    f"Not recommended unless you need to extend the term."
                )
            else:
                rec = "Same monthly payment — no financial benefit to refinancing."

            refi = RefinanceComparison(
                current=summary,
                refinanced=refi_summary,
                monthly_savings=monthly_savings,
                lifetime_interest_savings=interest_savings,
                break_even_months=break_even,
                break_even_date=_iso_month(today, break_even),
                recommendation=rec,
            )

        milestones = _equity_milestones(balance, rows, today)

        return MortgageAnalysis(
            loan_balance=round(balance, 2),
            interest_rate=round(rate, 6),
            monthly_payment=pmt,
            remaining_months=months,
            amortization=rows,
            summary=summary,
            refinance=refi,
            extra_payment=extra_impact,
            equity_milestones=milestones,
        )
