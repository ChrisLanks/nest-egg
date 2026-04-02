"""Tax projection and estimated quarterly tax service.

Estimates the current-year federal income tax liability and quarterly
estimated payment amounts based on transaction income/expense data
already in the database.

Scope
-----
- Ordinary income tax (W-2 and self-employment income)
- Long-term capital gains (from holdings unrealised/realised data)
- Standard deduction (auto-applied; itemised deduction inputs optional)
- Self-employment tax (15.3% on net SE income, 50% deductible)
- Quarterly payment schedule (IRS Form 1040-ES due dates)
- Under-payment safe harbour check (90% of current year or 100% of prior)

Limitations
-----------
- Federal only — no state income tax
- Does not handle AMT, credits, or complex business income
- Relies on transaction labels/categories for income classification
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import FICA, SS, TAX
from app.constants.state_tax_rates import STATE_NAMES
from app.models.account import Account
from app.models.transaction import Transaction
from app.services.roth_conversion_service import _get_brackets, _standard_deduction
from app.services.tax_rate_providers import get_provider

logger = logging.getLogger(__name__)

# IRS quarterly due dates (month, day) for each payment period
# Q1: Jan 1–Mar 31 → due Apr 15
# Q2: Apr 1–May 31 → due Jun 15
# Q3: Jun 1–Aug 31 → due Sep 15
# Q4: Sep 1–Dec 31 → due Jan 15 next year
_QUARTERLY_DEADLINES = [
    (4, 15, "Q1"),
    (6, 15, "Q2"),
    (9, 15, "Q3"),
    (1, 15, "Q4"),  # next year
]


@dataclass
class TaxBracketBreakdown:
    """Tax owed in a single bracket."""

    rate: float
    income_in_bracket: float
    tax_owed: float


@dataclass
class QuarterlyPayment:
    """One IRS estimated payment."""

    quarter: str  # "Q1", "Q2", "Q3", "Q4"
    due_date: str  # ISO date
    amount_due: float
    paid: bool = False  # always False until we track payments


@dataclass
class TaxProjection:
    """Full current-year tax projection."""

    tax_year: int
    filing_status: str
    # Income components
    ordinary_income: float
    self_employment_income: float
    estimated_capital_gains: float
    total_gross_income: float
    # Deductions
    standard_deduction: float
    se_deduction: float  # 50% of SE tax
    additional_deductions: float
    total_deductions: float
    taxable_income: float
    # Tax components
    ordinary_tax: float
    se_tax: float
    ltcg_tax: float
    niit: float
    total_tax_before_credits: float
    effective_rate: float
    marginal_rate: float
    # Quarterly payments
    quarterly_payments: list[QuarterlyPayment]
    total_quarterly_due: float
    # Safe harbour
    prior_year_tax: Optional[float]
    safe_harbour_amount: Optional[float]
    safe_harbour_met: Optional[bool]
    # Breakdown
    bracket_breakdown: list[TaxBracketBreakdown]
    summary: str
    # State tax (optional — defaults so must come last)
    state: Optional[str] = None  # state abbreviation e.g. "CA"
    state_tax: float = 0.0
    state_tax_rate: float = 0.0
    combined_tax: float = 0.0  # total_tax_before_credits + state_tax
    combined_effective_rate: float = 0.0
    # Provider metadata
    provider_source: Optional[str] = None
    provider_tax_year: Optional[int] = None


# ── Helpers ────────────────────────────────────────────────────────────────


def _ordinary_tax(
    taxable_income: float, filing_status: str
) -> tuple[float, list[TaxBracketBreakdown]]:
    """Compute ordinary income tax and bracket breakdown."""
    brackets = _get_brackets(filing_status, 0)
    tax = 0.0
    breakdown: list[TaxBracketBreakdown] = []
    prev_ceiling = 0.0

    for rate, ceiling in brackets:
        if taxable_income <= prev_ceiling:
            break
        income_in = min(taxable_income, ceiling) - prev_ceiling
        if income_in <= 0:
            prev_ceiling = ceiling
            continue
        owed = round(income_in * rate, 2)
        breakdown.append(
            TaxBracketBreakdown(rate=rate, income_in_bracket=round(income_in, 2), tax_owed=owed)
        )
        tax += owed
        prev_ceiling = ceiling
        if ceiling == float("inf"):
            break

    return round(tax, 2), breakdown


def _ltcg_tax(gains: float, ordinary_taxable: float, filing_status: str) -> float:
    """Compute LTCG tax. Gains are stacked on top of ordinary income."""
    if gains <= 0:
        return 0.0
    brackets = TAX.LTCG_BRACKETS_SINGLE if filing_status == "single" else TAX.LTCG_BRACKETS_MARRIED
    tax = 0.0
    base = ordinary_taxable  # LTCG stacks on top
    remaining_gains = gains

    for threshold, rate in brackets:
        if base >= threshold:
            continue  # already past this bracket — don't modify base
        room = threshold - base
        taxable_at_rate = min(remaining_gains, room)
        tax += round(taxable_at_rate * rate, 2)
        base += taxable_at_rate
        remaining_gains -= taxable_at_rate
        if remaining_gains <= 0:
            break

    # Any remaining gains above highest threshold
    if remaining_gains > 0:
        tax += round(remaining_gains * brackets[-1][1], 2)

    return round(tax, 2)


def _quarterly_schedule(total_tax: float, today: date) -> list[QuarterlyPayment]:
    """Divide total estimated tax into four quarterly payments."""
    per_quarter = round(total_tax / 4, 2)
    remainder = round(total_tax - per_quarter * 3, 2)
    year = today.year
    payments = []
    for i, (month, day, label) in enumerate(_QUARTERLY_DEADLINES):
        due_year = year if month != 1 else year + 1
        due_date = date(due_year, month, day).isoformat()
        amount = remainder if i == 3 else per_quarter
        payments.append(QuarterlyPayment(quarter=label, due_date=due_date, amount_due=amount))
    return payments


# ── Service ────────────────────────────────────────────────────────────────


class TaxProjectionService:
    """
    Estimates current-year federal tax liability from transaction data.

    Usage::

        svc = TaxProjectionService(db)
        result = await svc.project(
            organization_id=org_id,
            user_id=user_id,
            filing_status="single",
            self_employment_income=0,
            additional_deductions=0,
            prior_year_tax=None,
        )
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def project(
        self,
        organization_id: UUID,
        user_id: Optional[UUID],
        filing_status: str = "single",
        self_employment_income: float = 0.0,
        estimated_capital_gains: float = 0.0,
        additional_deductions: float = 0.0,
        prior_year_tax: Optional[float] = None,
        state: Optional[str] = None,
        today: Optional[date] = None,
    ) -> TaxProjection:
        """
        Build a full-year tax projection.

        Income is sourced from positive transactions (non-transfer) YTD,
        then annualised to a full-year estimate based on days elapsed.

        Parameters
        ----------
        filing_status:
            "single" or "married".
        self_employment_income:
            Net self-employment income (user-provided; not in transaction data).
        estimated_capital_gains:
            Long-term capital gains expected this year (user-provided).
        additional_deductions:
            Itemised deductions beyond standard (mortgage interest, charitable, etc.).
        prior_year_tax:
            Last year's total tax (for safe harbour calculation).
        """
        if today is None:
            today = date.today()

        # Normalise filing_status so comparisons are case-insensitive throughout
        # ("Married", "MFJ", "married" etc. all resolve correctly).
        filing_status = filing_status.lower().strip()
        if filing_status not in ("single", "married"):
            filing_status = "single"

        tax_year = today.year

        # Annualise income from YTD transactions
        ytd_income = await self._ytd_income(organization_id, user_id, tax_year)
        days_elapsed = (today - date(tax_year, 1, 1)).days + 1
        import calendar
        days_in_year = 366 if calendar.isleap(tax_year) else 365
        annualisation_factor = days_in_year / max(days_elapsed, 1)
        annualised_income = round(ytd_income * annualisation_factor, 2)

        ordinary_income = max(0.0, annualised_income + self_employment_income)

        # Self-employment tax: SS portion capped at taxable max + Medicare + Additional Medicare
        if self_employment_income > 0:
            se_ss = min(self_employment_income, SS.TAXABLE_MAX) * float(FICA.SS_SELF_EMPLOYED_RATE)
            se_medicare = self_employment_income * float(FICA.MEDICARE_SELF_EMPLOYED_RATE)
            # Additional Medicare Tax on SE income above threshold
            additional_medicare_threshold = (
                TAX.ADDITIONAL_MEDICARE_THRESHOLD_MARRIED
                if filing_status.lower() in ("married", "mfj")
                else TAX.ADDITIONAL_MEDICARE_THRESHOLD_SINGLE
            )
            se_additional_medicare = max(0, self_employment_income - additional_medicare_threshold) * float(FICA.ADDITIONAL_MEDICARE_RATE)
            se_tax = round(se_ss + se_medicare + se_additional_medicare, 2)
        else:
            se_tax = 0.0
        se_deduction = round(se_tax * 0.50, 2)  # 50% of SE tax is deductible

        # Standard deduction (current year)
        std_ded = _standard_deduction(filing_status, 0)
        total_deductions = std_ded + se_deduction + additional_deductions
        taxable_income = max(0.0, ordinary_income - total_deductions)

        # Ordinary income tax
        ordinary_tax, bracket_breakdown = _ordinary_tax(taxable_income, filing_status)

        # LTCG tax (stacked on top of ordinary)
        ltcg_tax = _ltcg_tax(estimated_capital_gains, taxable_income, filing_status)

        # NIIT: 3.8% on lesser of (net investment income) or (MAGI - threshold)
        magi = ordinary_income + estimated_capital_gains
        nii_threshold = (
            TAX.NII_THRESHOLD_MARRIED if filing_status.lower() in ("married", "mfj")
            else TAX.NII_THRESHOLD_SINGLE
        )
        niit = 0.0
        if magi > nii_threshold:
            net_investment_income = estimated_capital_gains  # best available proxy
            niit = round(min(net_investment_income, magi - nii_threshold) * float(TAX.NII_SURTAX_RATE), 2)

        total_tax = round(ordinary_tax + se_tax + ltcg_tax + niit, 2)
        effective_rate = round(total_tax / ordinary_income, 4) if ordinary_income > 0 else 0.0
        # When taxable income is 0 (e.g. income fully covered by standard deduction)
        # show the first bracket rate as marginal, since that's what applies to the next dollar.
        if bracket_breakdown:
            marginal_rate = bracket_breakdown[-1].rate
        else:
            brackets = _get_brackets(filing_status, 0)
            marginal_rate = brackets[0][0] if brackets else 0.0

        # State income tax — use pluggable provider for bracket-aware rates
        state_upper = state.upper() if state else None
        provider = await get_provider()
        if state_upper:
            state_tax_rate = await provider.get_rate(state_upper, filing_status, taxable_income)
        else:
            state_tax_rate = 0.0
        state_tax = round(taxable_income * state_tax_rate, 2) if state_upper else 0.0
        combined_tax = round(total_tax + state_tax, 2)
        combined_effective_rate = (
            round(combined_tax / ordinary_income, 4) if ordinary_income > 0 else 0.0
        )

        # Quarterly payments
        quarterly = _quarterly_schedule(total_tax, today)
        total_quarterly = round(sum(q.amount_due for q in quarterly), 2)

        # Safe harbour
        safe_harbour: Optional[float] = None
        safe_harbour_met: Optional[bool] = None
        if prior_year_tax is not None and prior_year_tax > 0:
            # AGI > $150k: must pay 110% of prior-year tax; else 100%
            agi_estimate = ordinary_income + estimated_capital_gains
            sh_rate = 1.10 if agi_estimate > 150_000 else 1.00
            safe_harbour = round(prior_year_tax * sh_rate, 2)
            safe_harbour_met = total_quarterly >= safe_harbour

        summary = self._build_summary(
            ordinary_income,
            taxable_income,
            total_tax,
            effective_rate,
            marginal_rate,
            se_tax,
            ltcg_tax,
            filing_status,
            quarterly,
            state=state_upper,
            state_tax=state_tax,
            state_tax_rate=state_tax_rate,
        )

        return TaxProjection(
            tax_year=tax_year,
            filing_status=filing_status,
            ordinary_income=round(ordinary_income, 2),
            self_employment_income=round(self_employment_income, 2),
            estimated_capital_gains=round(estimated_capital_gains, 2),
            total_gross_income=round(ordinary_income + estimated_capital_gains, 2),
            standard_deduction=round(std_ded, 2),
            se_deduction=round(se_deduction, 2),
            additional_deductions=round(additional_deductions, 2),
            total_deductions=round(total_deductions, 2),
            taxable_income=round(taxable_income, 2),
            ordinary_tax=round(ordinary_tax, 2),
            se_tax=round(se_tax, 2),
            ltcg_tax=round(ltcg_tax, 2),
            niit=niit,
            total_tax_before_credits=total_tax,
            effective_rate=effective_rate,
            marginal_rate=marginal_rate,
            state=state_upper,
            state_tax=state_tax,
            state_tax_rate=state_tax_rate,
            combined_tax=combined_tax,
            combined_effective_rate=combined_effective_rate,
            quarterly_payments=quarterly,
            total_quarterly_due=total_quarterly,
            prior_year_tax=prior_year_tax,
            safe_harbour_amount=safe_harbour,
            safe_harbour_met=safe_harbour_met,
            bracket_breakdown=bracket_breakdown,
            summary=summary,
            provider_source=provider.source_name() if state_upper else None,
            provider_tax_year=provider.tax_year() if state_upper else None,
        )

    async def _ytd_income(
        self,
        organization_id: UUID,
        user_id: Optional[UUID],
        tax_year: int,
    ) -> float:
        """Sum positive (income) transactions YTD for the given org/user."""
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
            Transaction.date >= date(tax_year, 1, 1),
            Transaction.amount > 0,
            Transaction.is_transfer.is_(False),
        ]
        if user_id:
            conditions.append(Account.user_id == user_id)

        result = await self.db.execute(
            select(func.sum(Transaction.amount))
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
        )
        total = result.scalar() or 0
        return float(total)

    @staticmethod
    def _build_summary(
        ordinary_income: float,
        taxable_income: float,
        total_tax: float,
        effective_rate: float,
        marginal_rate: float,
        se_tax: float,
        ltcg_tax: float,
        filing_status: str,
        quarterly: list[QuarterlyPayment],
        state: Optional[str] = None,
        state_tax: float = 0.0,
        state_tax_rate: float = 0.0,
    ) -> str:
        parts = [
            f"Estimated {date.today().year} federal tax: ${total_tax:,.0f} "
            f"on ${ordinary_income:,.0f} gross income "
            f"(effective rate {effective_rate * 100:.1f}%, marginal {marginal_rate * 100:.0f}%)."
        ]
        if se_tax > 0:
            parts.append(f"Self-employment tax: ${se_tax:,.0f}.")
        if ltcg_tax > 0:
            parts.append(f"Capital gains tax: ${ltcg_tax:,.0f}.")
        if state:
            state_name = STATE_NAMES.get(state, state)
            if state_tax_rate == 0.0:
                # True no-income-tax state (e.g. TX, FL, WA) — rate is inherently 0
                parts.append(f"{state_name} has no state income tax.")
            elif state_tax > 0:
                combined = total_tax + state_tax
                parts.append(
                    f"{state_name} state income tax: ${state_tax:,.0f}. "
                    f"Combined federal + state: ${combined:,.0f}."
                )
            else:
                # State has income tax but taxable income is 0 (fully covered by deductions)
                parts.append(
                    f"{state_name} state income tax: $0 (income fully offset by deductions)."
                )
        else:
            parts.append("Federal only — does not include state taxes or credits.")
        next_due = next((q for q in quarterly if not q.paid), None)
        if next_due:
            parts.append(
                f"Next quarterly payment: ${next_due.amount_due:,.0f} "
                f"due {next_due.due_date} ({next_due.quarter})."
            )
        return " ".join(parts)
