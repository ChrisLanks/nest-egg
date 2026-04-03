"""
Tax bucket analysis service.

Analyzes the distribution of retirement assets across tax treatment buckets
(pre-tax, Roth, taxable, tax-free/HSA) and projects RMD tax bomb risk.
"""
from __future__ import annotations
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import RMD, TAX, TAX_BUCKETS
from app.models.account import Account, TaxTreatment
from app.utils.account_type_groups import TAX_TREATMENT_DEFAULTS


class TaxBucketService:

    @staticmethod
    async def get_bucket_summary(
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> dict:
        """
        Returns account balances grouped by tax treatment bucket.
        """
        # Build query
        stmt = select(Account).where(
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
        )
        if user_id:
            stmt = stmt.where(Account.user_id == user_id)
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        buckets: dict[str, Decimal] = {
            "pre_tax": Decimal("0"),
            "roth": Decimal("0"),
            "taxable": Decimal("0"),
            "tax_free": Decimal("0"),  # HSA
            "other": Decimal("0"),
        }

        for acct in accounts:
            balance = acct.current_balance or Decimal("0")
            if balance <= 0:
                continue
            # Use explicit tax_treatment if set; otherwise infer from account type.
            # Investment/brokerage accounts without a treatment default to TAXABLE.
            treatment = acct.tax_treatment or TAX_TREATMENT_DEFAULTS.get(
                acct.account_type, TaxTreatment.TAXABLE
            )
            if treatment == TaxTreatment.PRE_TAX:
                buckets["pre_tax"] += balance
            elif treatment == TaxTreatment.ROTH:
                buckets["roth"] += balance
            elif treatment == TaxTreatment.TAXABLE:
                buckets["taxable"] += balance
            elif treatment == TaxTreatment.TAX_FREE:
                buckets["tax_free"] += balance
            else:
                buckets["other"] += balance

        total = sum(buckets.values())
        retirement_total = buckets["pre_tax"] + buckets["roth"] + buckets["tax_free"]

        pre_tax_pct = (
            buckets["pre_tax"] / retirement_total if retirement_total > 0 else Decimal("0")
        )
        imbalanced = pre_tax_pct >= TAX_BUCKETS.PRE_TAX_WARNING_THRESHOLD_PCT

        return {
            "buckets": {k: float(v) for k, v in buckets.items()},
            "total": float(total),
            "retirement_total": float(retirement_total),
            "pre_tax_pct": float(pre_tax_pct),
            "imbalanced": imbalanced,
        }

    @staticmethod
    def project_rmd_schedule(
        pre_tax_balance: Decimal,
        current_age: int,
        growth_rate: Decimal | None = None,
    ) -> list[dict]:
        """
        Projects annual RMDs from the given pre-tax balance starting at RMD start age.
        Uses IRS Uniform Lifetime Table divisors (hardcoded key ages).
        """
        if growth_rate is None:
            growth_rate = TAX_BUCKETS.DEFAULT_GROWTH_RATE

        # Use the canonical Uniform Lifetime Table from constants (no duplicate)
        ULT = RMD.UNIFORM_LIFETIME_TABLE

        rmd_start_age = RMD.TRIGGER_AGE
        schedule = []
        balance = pre_tax_balance

        for age in range(max(current_age, rmd_start_age), 101):
            # Grow balance at start of year before RMD
            balance = balance * (1 + growth_rate)
            divisor = ULT.get(age, Decimal("5.0"))
            rmd = balance / divisor
            balance -= rmd
            schedule.append({
                "age": age,
                "rmd_amount": float(round(rmd, 2)),
                "remaining_balance": float(round(balance, 2)),
            })

        return schedule

    @staticmethod
    def get_roth_conversion_headroom(
        current_taxable_income: Decimal,
        filing_status: str,
        target_bracket_rate: Decimal | None = None,
    ) -> dict:
        """
        Returns how much can be Roth-converted while staying within the target bracket.
        Uses TAX class bracket data.
        """
        if target_bracket_rate is None:
            target_bracket_rate = TAX_BUCKETS.OPTIMAL_CONVERSION_BRACKET

        # Get bracket ceiling from TAX constants
        # BRACKETS_SINGLE/MARRIED are lists of (rate, ceiling) tuples
        key = "BRACKETS_MARRIED" if filing_status.lower() == "married" else "BRACKETS_SINGLE"
        brackets = getattr(TAX, key, None)

        ceiling = Decimal("0")
        for rate, threshold in (brackets or []):
            if Decimal(str(rate)) == target_bracket_rate:
                ceiling = Decimal(str(threshold))
                break

        headroom = max(Decimal("0"), ceiling - current_taxable_income)
        return {
            "target_bracket": float(target_bracket_rate),
            "bracket_ceiling": float(ceiling),
            "current_income": float(current_taxable_income),
            "conversion_headroom": float(headroom),
        }
