"""Required Minimum Distribution (RMD) calculator utility.

RMD rules:
- Required for Traditional IRA, 401(k), SEP IRA, SIMPLE IRA starting at age 73
- Roth IRAs do NOT require RMDs during the owner's lifetime
- Formula: Account balance ÷ Life expectancy factor from IRS Uniform Lifetime Table
"""

from datetime import date
from decimal import Decimal
from typing import Optional


# IRS Uniform Lifetime Table (2022+)
# Maps age to distribution period (life expectancy factor)
UNIFORM_LIFETIME_TABLE = {
    73: Decimal("26.5"),
    74: Decimal("25.5"),
    75: Decimal("24.6"),
    76: Decimal("23.7"),
    77: Decimal("22.9"),
    78: Decimal("22.0"),
    79: Decimal("21.1"),
    80: Decimal("20.2"),
    81: Decimal("19.4"),
    82: Decimal("18.5"),
    83: Decimal("17.7"),
    84: Decimal("16.8"),
    85: Decimal("16.0"),
    86: Decimal("15.2"),
    87: Decimal("14.4"),
    88: Decimal("13.7"),
    89: Decimal("12.9"),
    90: Decimal("12.2"),
    91: Decimal("11.5"),
    92: Decimal("10.8"),
    93: Decimal("10.1"),
    94: Decimal("9.5"),
    95: Decimal("8.9"),
    96: Decimal("8.4"),
    97: Decimal("7.8"),
    98: Decimal("7.3"),
    99: Decimal("6.8"),
    100: Decimal("6.4"),
    101: Decimal("6.0"),
    102: Decimal("5.6"),
    103: Decimal("5.2"),
    104: Decimal("4.9"),
    105: Decimal("4.6"),
    106: Decimal("4.3"),
    107: Decimal("4.1"),
    108: Decimal("3.9"),
    109: Decimal("3.7"),
    110: Decimal("3.5"),
    111: Decimal("3.4"),
    112: Decimal("3.3"),
    113: Decimal("3.1"),
    114: Decimal("3.0"),
    115: Decimal("2.9"),
    116: Decimal("2.8"),
    117: Decimal("2.7"),
    118: Decimal("2.5"),
    119: Decimal("2.3"),
    120: Decimal("2.0"),
}


def calculate_age(birthdate: date, as_of_date: Optional[date] = None) -> int:
    """Calculate age in years as of a given date (defaults to today)."""
    if as_of_date is None:
        as_of_date = date.today()

    age = as_of_date.year - birthdate.year

    # Adjust if birthday hasn't occurred yet this year
    if (as_of_date.month, as_of_date.day) < (birthdate.month, birthdate.day):
        age -= 1

    return age


def requires_rmd(age: int) -> bool:
    """Check if a person of given age requires RMD withdrawals.

    RMD age is 73 as of 2023 (SECURE 2.0 Act).
    """
    return age >= 73


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
    penalty_rate = Decimal("0.25")  # 25%
    return (shortfall * penalty_rate).quantize(Decimal("0.01"))
