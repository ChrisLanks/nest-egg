"""Required Minimum Distribution (RMD) calculator utility.

RMD rules:
- Required for Traditional IRA, 401(k), SEP IRA, SIMPLE IRA starting at age 73
- Roth IRAs do NOT require RMDs during the owner's lifetime
- Formula: Account balance ÷ Life expectancy factor from IRS Uniform Lifetime Table
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from app.constants.financial import RMD as RMD_CONSTANTS

# Re-export from centralized constants for backward compatibility
UNIFORM_LIFETIME_TABLE = RMD_CONSTANTS.UNIFORM_LIFETIME_TABLE


def calculate_age(birthdate: date, as_of_date: Optional[date] = None) -> int:
    """Calculate age in years as of a given date (defaults to today)."""
    if as_of_date is None:
        as_of_date = date.today()

    age = as_of_date.year - birthdate.year

    # Adjust if birthday hasn't occurred yet this year
    if (as_of_date.month, as_of_date.day) < (birthdate.month, birthdate.day):
        age -= 1

    return age


def requires_rmd(age: int, birth_year: int | None = None) -> bool:
    """Check if a person of given age requires RMD withdrawals.

    SECURE 2.0: Age 73 for born before 1960, age 75 for born 1960+.
    """
    trigger = RMD_CONSTANTS.trigger_age_for_birth_year(birth_year)
    return age >= trigger


def calculate_rmd(account_balance: Decimal, age: int) -> Optional[Decimal]:
    """Calculate Required Minimum Distribution for a given age and balance.

    Args:
        account_balance: Total balance in retirement account as of Dec 31 prior year
        age: Account owner's age on December 31 of the current year

    Returns:
        Required minimum distribution amount, or None if not applicable
    """
    if not requires_rmd(age):
        return None

    # Get life expectancy factor from IRS table
    life_expectancy_factor = UNIFORM_LIFETIME_TABLE.get(age)

    if life_expectancy_factor is None:
        # For ages > 120, use the last available factor
        life_expectancy_factor = UNIFORM_LIFETIME_TABLE[120]

    # Calculate RMD
    rmd = account_balance / life_expectancy_factor

    return rmd.quantize(Decimal("0.01"))  # Round to cents


def get_rmd_deadline(year: int) -> date:
    """Get RMD withdrawal deadline for a given year.

    Standard deadline: December 31 of the year
    First RMD: Can be delayed until April 1 of following year (not handled here)
    """
    return date(year, 12, 31)


def calculate_rmd_penalty(shortfall: Decimal) -> Decimal:
    """Calculate penalty for RMD shortfall.

    Penalty is 25% of the amount not withdrawn (reduced from 50% by SECURE 2.0).
    Penalty can be reduced to 10% if corrected within 2 years.
    """
    penalty_rate = RMD_CONSTANTS.PENALTY_RATE
    return (shortfall * penalty_rate).quantize(Decimal("0.01"))
