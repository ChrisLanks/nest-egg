"""Private Equity Performance Metrics Service.

Calculates IRR, TVPI, DPI for PE/PD accounts from their transaction history.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional

logger = logging.getLogger(__name__)


def calculate_tvpi(
    total_distributions: Decimal,
    current_nav: Decimal,
    total_called: Decimal,
) -> float:
    """TVPI = (distributions + NAV) / capital_called."""
    if total_called <= 0:
        return 0.0
    return float((total_distributions + current_nav) / total_called)


def calculate_dpi(
    total_distributions: Decimal,
    total_called: Decimal,
) -> float:
    """DPI = distributions / capital_called (realized returns only)."""
    if total_called <= 0:
        return 0.0
    return float(total_distributions / total_called)


def calculate_irr(
    cash_flows: List[tuple],  # list of (date, amount) — calls negative, distributions positive
    current_nav: Decimal,
    nav_date: date,
    max_iterations: int = 100,
    tolerance: float = 1e-6,
) -> Optional[float]:
    """Calculate IRR using Newton's method.

    cash_flows: list of (date, amount) where capital calls are negative,
                distributions are positive
    current_nav: current NAV added as final positive cash flow
    nav_date: date of the current NAV

    Returns annualized IRR as a decimal (e.g. 0.12 = 12%), or None if
    convergence fails.
    """
    if not cash_flows and current_nav <= 0:
        return None

    # Build full cash flow list with dates
    flows = list(cash_flows)
    flows.append((nav_date, float(current_nav)))

    if len(flows) < 2:
        return None

    # Sort by date
    flows.sort(key=lambda x: x[0])
    base_date = flows[0][0]

    # Convert dates to year fractions
    year_fracs = []
    amounts = []
    for dt, amt in flows:
        year_frac = (dt - base_date).days / 365.25
        year_fracs.append(year_frac)
        amounts.append(float(amt))

    # Newton-Raphson to find IRR
    rate = 0.10  # Initial guess: 10%

    for _ in range(max_iterations):
        npv = 0.0
        d_npv = 0.0
        for i, (t, cf) in enumerate(zip(year_fracs, amounts)):
            denom = (1 + rate) ** t
            if denom == 0:
                return None
            npv += cf / denom
            if t > 0:
                d_npv -= t * cf / ((1 + rate) ** (t + 1))

        if abs(d_npv) < 1e-14:
            # Derivative too small, try bisection fallback
            break

        new_rate = rate - npv / d_npv

        # Clamp to prevent divergence
        if new_rate < -0.99:
            new_rate = -0.99
        if new_rate > 10.0:
            new_rate = 10.0

        if abs(new_rate - rate) < tolerance:
            return round(new_rate, 6)

        rate = new_rate

    # Fallback: return last estimate if close enough
    return round(rate, 6) if abs(npv) < 0.01 else None


def compute_pe_metrics(
    transactions: list,  # list of dicts with type, amount, date
    current_nav: Decimal,
    nav_date: Optional[date] = None,
) -> dict:
    """Compute all PE metrics from a list of transactions.

    transactions: list of dicts:
        {"type": "capital_call"|"distribution"|"nav_update",
         "amount": Decimal, "date": date}
    """
    if nav_date is None:
        nav_date = date.today()

    total_called = Decimal("0")
    total_distributions = Decimal("0")
    cash_flows = []

    for txn in transactions:
        txn_type = txn["type"]
        amount = Decimal(str(txn["amount"]))
        txn_date = txn["date"]

        if txn_type == "capital_call":
            total_called += amount
            cash_flows.append((txn_date, -float(amount)))
        elif txn_type == "distribution":
            total_distributions += amount
            cash_flows.append((txn_date, float(amount)))
        # nav_update transactions don't affect cash flows

    tvpi = calculate_tvpi(total_distributions, current_nav, total_called)
    dpi = calculate_dpi(total_distributions, total_called)
    irr = calculate_irr(cash_flows, current_nav, nav_date)

    return {
        "total_called": float(total_called),
        "total_distributions": float(total_distributions),
        "current_nav": float(current_nav),
        "tvpi": round(tvpi, 4),
        "dpi": round(dpi, 4),
        "irr": irr,
        "irr_pct": round(irr * 100, 2) if irr is not None else None,
        "moic": round(tvpi, 4),  # MOIC is same as TVPI
        "net_profit": float(total_distributions + current_nav - total_called),
    }
