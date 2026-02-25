"""Tax-optimized and simple withdrawal strategy service.

Implements two withdrawal approaches:
1. Tax-optimized: Taxable → Tax-Deferred → Roth → HSA (satisfying RMDs first)
2. Simple rate: Fixed percentage of total portfolio (e.g., 4% rule)

Used by Monte Carlo simulation to compare strategy outcomes.
"""

from decimal import Decimal
from typing import Optional

from app.utils.rmd_calculator import calculate_rmd, UNIFORM_LIFETIME_TABLE


class AccountBuckets:
    """Tracks balances across tax-treatment buckets during simulation."""

    __slots__ = ("taxable", "pre_tax", "roth", "hsa")

    def __init__(
        self,
        taxable: float = 0.0,
        pre_tax: float = 0.0,
        roth: float = 0.0,
        hsa: float = 0.0,
    ):
        self.taxable = taxable
        self.pre_tax = pre_tax
        self.roth = roth
        self.hsa = hsa

    @property
    def total(self) -> float:
        return self.taxable + self.pre_tax + self.roth + self.hsa

    def apply_return(self, annual_return: float) -> None:
        """Apply investment return to all buckets."""
        factor = 1 + annual_return
        self.taxable *= factor
        self.pre_tax *= factor
        self.roth *= factor
        self.hsa *= factor

    def clone(self) -> "AccountBuckets":
        return AccountBuckets(self.taxable, self.pre_tax, self.roth, self.hsa)


def compute_rmd_amount(pre_tax_balance: float, age: int) -> float:
    """Compute Required Minimum Distribution for a given age and balance.

    RMDs are required at age 73+ from pre-tax accounts.
    """
    if age < 73 or pre_tax_balance <= 0:
        return 0.0

    # Use the Uniform Lifetime Table factor
    factor = UNIFORM_LIFETIME_TABLE.get(age)
    if factor is None:
        # Age > 120, use minimum factor
        factor = UNIFORM_LIFETIME_TABLE.get(120, Decimal("2.0"))

    return round(pre_tax_balance / float(factor), 2)


def tax_optimized_withdrawal(
    buckets: AccountBuckets,
    needed: float,
    age: int,
    federal_rate: float,
    state_rate: float,
    capital_gains_rate: float,
) -> dict:
    """Withdraw using tax-optimized ordering.

    Order: Satisfy RMDs first → Taxable → Tax-Deferred → Roth → HSA.
    Returns dict with withdrawal details and taxes paid.
    """
    remaining = needed
    taxes = 0.0
    withdrawals = {"taxable": 0.0, "pre_tax": 0.0, "roth": 0.0, "hsa": 0.0}

    # Step 1: Satisfy RMDs from pre-tax accounts
    rmd = compute_rmd_amount(buckets.pre_tax, age)
    if rmd > 0:
        actual_rmd = min(rmd, buckets.pre_tax)
        buckets.pre_tax -= actual_rmd
        withdrawals["pre_tax"] += actual_rmd
        # RMDs are taxed as ordinary income
        rmd_tax = actual_rmd * (federal_rate + state_rate)
        taxes += rmd_tax
        # RMD counts toward needed withdrawal (net of taxes)
        remaining -= (actual_rmd - rmd_tax)

    if remaining <= 0:
        return {"withdrawals": withdrawals, "taxes": taxes, "rmd_amount": rmd}

    # Step 2: Taxable accounts (capital gains tax only)
    if buckets.taxable > 0 and remaining > 0:
        # Need to withdraw enough to cover remaining + capital gains tax
        # gross * (1 - cap_gains_rate) = remaining → gross = remaining / (1 - cap_gains_rate)
        gross_needed = remaining / max(1 - capital_gains_rate, 0.01)
        actual = min(gross_needed, buckets.taxable)
        buckets.taxable -= actual
        withdrawals["taxable"] += actual
        tax = actual * capital_gains_rate
        taxes += tax
        remaining -= (actual - tax)

    # Step 3: Tax-deferred (ordinary income tax)
    if buckets.pre_tax > 0 and remaining > 0:
        income_rate = federal_rate + state_rate
        gross_needed = remaining / max(1 - income_rate, 0.01)
        actual = min(gross_needed, buckets.pre_tax)
        buckets.pre_tax -= actual
        withdrawals["pre_tax"] += actual
        tax = actual * income_rate
        taxes += tax
        remaining -= (actual - tax)

    # Step 4: Roth (tax-free qualified withdrawals)
    if buckets.roth > 0 and remaining > 0:
        actual = min(remaining, buckets.roth)
        buckets.roth -= actual
        withdrawals["roth"] += actual
        remaining -= actual

    # Step 5: HSA (tax-free for medical, otherwise taxed + 20% penalty if < 65)
    if buckets.hsa > 0 and remaining > 0:
        actual = min(remaining, buckets.hsa)
        buckets.hsa -= actual
        withdrawals["hsa"] += actual
        # Assume medical expenses justify HSA withdrawal (tax-free)
        remaining -= actual

    return {"withdrawals": withdrawals, "taxes": round(taxes, 2), "rmd_amount": rmd}


def simple_rate_withdrawal(
    buckets: AccountBuckets,
    withdrawal_rate: float,
    federal_rate: float,
    state_rate: float,
    capital_gains_rate: float,
) -> dict:
    """Withdraw a fixed percentage of total portfolio (e.g., 4% rule).

    Draws proportionally from all buckets.
    """
    total = buckets.total
    if total <= 0:
        return {"withdrawals": {"taxable": 0, "pre_tax": 0, "roth": 0, "hsa": 0}, "taxes": 0.0}

    gross_withdrawal = total * withdrawal_rate
    taxes = 0.0
    withdrawals = {"taxable": 0.0, "pre_tax": 0.0, "roth": 0.0, "hsa": 0.0}

    # Pro-rata from each bucket
    for bucket_name in ("taxable", "pre_tax", "roth", "hsa"):
        balance = getattr(buckets, bucket_name)
        if balance <= 0:
            continue
        share = (balance / total) * gross_withdrawal
        actual = min(share, balance)
        setattr(buckets, bucket_name, balance - actual)
        withdrawals[bucket_name] = actual

        # Tax calculation per bucket
        if bucket_name == "taxable":
            taxes += actual * capital_gains_rate
        elif bucket_name == "pre_tax":
            taxes += actual * (federal_rate + state_rate)
        # Roth and HSA are tax-free (assuming qualified)

    return {"withdrawals": withdrawals, "taxes": round(taxes, 2)}


def run_withdrawal_comparison(
    initial_buckets: AccountBuckets,
    annual_spending: float,
    retirement_age: int,
    life_expectancy: int,
    annual_return: float,
    inflation_rate: float,
    withdrawal_rate: float,
    federal_rate: float,
    state_rate: float,
    capital_gains_rate: float,
    ss_annual: float = 0.0,
    pension_annual: float = 0.0,
) -> dict:
    """Run a single deterministic comparison of both strategies.

    Returns summary stats for each strategy (not full Monte Carlo).
    """
    results = {}

    for strategy_name, strategy_fn in [
        ("tax_optimized", "tax_optimized"),
        ("simple_rate", "simple_rate"),
    ]:
        buckets = initial_buckets.clone()
        total_taxes = 0.0
        depleted_age = None

        for year in range(life_expectancy - retirement_age + 1):
            age = retirement_age + year
            adjusted_spending = annual_spending * ((1 + inflation_rate) ** year)
            adjusted_income = (ss_annual + pension_annual) * ((1 + inflation_rate) ** year)
            net_needed = max(adjusted_spending - adjusted_income, 0)

            if buckets.total <= 0:
                if depleted_age is None:
                    depleted_age = age
                continue

            # Apply returns
            buckets.apply_return(annual_return)

            # Withdraw
            if strategy_name == "tax_optimized":
                result = tax_optimized_withdrawal(
                    buckets, net_needed, age,
                    federal_rate, state_rate, capital_gains_rate,
                )
            else:
                result = simple_rate_withdrawal(
                    buckets, withdrawal_rate,
                    federal_rate, state_rate, capital_gains_rate,
                )

            total_taxes += result["taxes"]

            if buckets.total <= 0 and depleted_age is None:
                depleted_age = age

        results[strategy_name] = {
            "final_portfolio": round(buckets.total, 2),
            "total_taxes_paid": round(total_taxes, 2),
            "depleted_age": depleted_age,
            "success": buckets.total > 0,
        }

    return results
