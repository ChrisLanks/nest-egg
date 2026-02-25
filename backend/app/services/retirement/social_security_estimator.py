"""Social Security benefit estimator.

Implements PIA (Primary Insurance Amount) estimation using 2024 bend points,
early/delayed claiming adjustments, and FRA (Full Retirement Age) lookup.
"""

from decimal import Decimal
from typing import Optional


# 2024 PIA bend points (monthly amounts)
BEND_POINT_1 = 1174  # First bend point
BEND_POINT_2 = 7078  # Second bend point

# Replacement rates at each segment
RATE_1 = 0.90  # 90% of first $1,174
RATE_2 = 0.32  # 32% between $1,174 and $7,078
RATE_3 = 0.15  # 15% above $7,078

# FRA by birth year
FRA_TABLE = {
    # birth_year: (years, months)
    1937: (65, 0),
    1938: (65, 2),
    1939: (65, 4),
    1940: (65, 6),
    1941: (65, 8),
    1942: (65, 10),
    # 1943-1954: FRA = 66
    1955: (66, 2),
    1956: (66, 4),
    1957: (66, 6),
    1958: (66, 8),
    1959: (66, 10),
    # 1960+: FRA = 67
}


def get_fra(birth_year: int) -> float:
    """Get Full Retirement Age for a given birth year.

    Returns age as a decimal (e.g., 66.5 for 66 years 6 months).
    """
    if birth_year <= 1937:
        return 65.0
    if 1943 <= birth_year <= 1954:
        return 66.0
    if birth_year >= 1960:
        return 67.0

    # Lookup transitional years
    entry = FRA_TABLE.get(birth_year)
    if entry:
        years, months = entry
        return years + months / 12
    return 67.0


def estimate_pia(aime: float) -> float:
    """Calculate PIA from Average Indexed Monthly Earnings using bend point formula.

    Args:
        aime: Average Indexed Monthly Earnings (monthly)

    Returns:
        Monthly PIA (Primary Insurance Amount) at FRA
    """
    if aime <= 0:
        return 0.0

    pia = 0.0

    # First segment: 90% of AIME up to first bend point
    pia += RATE_1 * min(aime, BEND_POINT_1)

    # Second segment: 32% of AIME between bend points
    if aime > BEND_POINT_1:
        pia += RATE_2 * min(aime - BEND_POINT_1, BEND_POINT_2 - BEND_POINT_1)

    # Third segment: 15% of AIME above second bend point
    if aime > BEND_POINT_2:
        pia += RATE_3 * (aime - BEND_POINT_2)

    return round(pia, 2)


def estimate_aime_from_salary(
    current_salary: float,
    current_age: int,
    career_start_age: int = 22,
) -> float:
    """Rough AIME estimate from current annual salary.

    Assumes salary grew ~2.5% per year from career start. Uses the
    highest 35 years of indexed earnings (simplified).

    Args:
        current_salary: Current annual salary
        current_age: Current age
        career_start_age: Age when career started (default 22)

    Returns:
        Estimated monthly AIME
    """
    if current_salary <= 0 or current_age <= career_start_age:
        return 0.0

    years_worked = current_age - career_start_age
    wage_growth = 0.025  # Assumed historical wage growth

    # Build earnings history (in today's dollars, roughly indexed)
    earnings = []
    for y in range(years_worked):
        # Estimate past salary: current_salary / (1 + growth)^(years_worked - y)
        years_ago = years_worked - y
        past_salary = current_salary / ((1 + wage_growth) ** years_ago)
        # Cap at Social Security taxable maximum (approximate: $168,600 for 2024)
        earnings.append(min(past_salary, 168600))

    # Use top 35 years (or all if less)
    earnings.sort(reverse=True)
    top_35 = earnings[:35]

    if not top_35:
        return 0.0

    # AIME = total earnings / (35 years * 12 months)
    total_earnings = sum(top_35)
    aime = total_earnings / (35 * 12)
    return round(aime, 2)


def adjust_for_claiming_age(
    pia: float,
    fra: float,
    claiming_age: int,
) -> float:
    """Adjust monthly benefit for early or delayed claiming.

    - Early claiming (before FRA): Reduced by ~6.67% per year for
      first 36 months early, then 5% per year beyond that.
    - Delayed claiming (after FRA): Increased by 8% per year up to age 70.

    Args:
        pia: Monthly PIA at FRA
        fra: Full Retirement Age (decimal)
        claiming_age: Age at which benefits are claimed

    Returns:
        Adjusted monthly benefit
    """
    if pia <= 0:
        return 0.0

    months_diff = round((claiming_age - fra) * 12)

    if months_diff == 0:
        return round(pia, 2)

    if months_diff < 0:
        # Early claiming reduction
        months_early = abs(months_diff)
        # First 36 months: 5/9 of 1% per month = ~6.67%/year
        first_36 = min(months_early, 36)
        reduction = first_36 * (5 / 9 / 100)
        # Beyond 36 months: 5/12 of 1% per month = 5%/year
        if months_early > 36:
            beyond_36 = months_early - 36
            reduction += beyond_36 * (5 / 12 / 100)
        adjusted = pia * (1 - reduction)
    else:
        # Delayed retirement credits: 8% per year = 2/3% per month
        months_delayed = min(months_diff, round((70 - fra) * 12))
        credit = months_delayed * (2 / 3 / 100)
        adjusted = pia * (1 + credit)

    return round(max(adjusted, 0), 2)


def estimate_social_security(
    current_salary: float,
    current_age: int,
    birth_year: int,
    claiming_age: int = 67,
    career_start_age: int = 22,
    manual_pia_override: Optional[float] = None,
) -> dict:
    """Full Social Security benefit estimation.

    Args:
        current_salary: Current annual salary
        current_age: Current age
        birth_year: Year of birth
        claiming_age: Planned claiming age (62-70)
        career_start_age: Age career started
        manual_pia_override: If set, use this PIA instead of estimating

    Returns:
        Dict with estimated_pia, monthly benefits at 62/FRA/70,
        fra_age, claiming_age, and monthly_benefit at chosen claiming age.
    """
    fra = get_fra(birth_year)

    if manual_pia_override is not None:
        pia = manual_pia_override
    else:
        aime = estimate_aime_from_salary(current_salary, current_age, career_start_age)
        pia = estimate_pia(aime)

    monthly_at_62 = adjust_for_claiming_age(pia, fra, 62)
    monthly_at_fra = round(pia, 2)
    monthly_at_70 = adjust_for_claiming_age(pia, fra, 70)
    monthly_at_claiming = adjust_for_claiming_age(pia, fra, claiming_age)

    return {
        "estimated_pia": round(pia, 2),
        "monthly_at_62": monthly_at_62,
        "monthly_at_fra": monthly_at_fra,
        "monthly_at_70": monthly_at_70,
        "fra_age": fra,
        "claiming_age": claiming_age,
        "monthly_benefit": monthly_at_claiming,
    }
