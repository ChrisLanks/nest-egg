"""Healthcare cost estimator for retirement planning.

Models healthcare costs across retirement phases:
- Pre-65: ACA marketplace insurance
- 65+: Medicare Part B + Part D + IRMAA surcharges
- 85+: Optional long-term care costs
All costs inflated by medical inflation rate.
"""

from app.constants.financial import HEALTHCARE, MEDICARE

# Re-export from centralized constants for backward compatibility
ACA_MONTHLY_SINGLE = HEALTHCARE.ACA_MONTHLY_SINGLE
ACA_MONTHLY_COUPLE = HEALTHCARE.ACA_MONTHLY_COUPLE
MEDICARE_PART_B_MONTHLY = MEDICARE.PART_B_MONTHLY
MEDICARE_PART_D_MONTHLY = MEDICARE.PART_D_MONTHLY
MEDIGAP_MONTHLY = MEDICARE.MEDIGAP_MONTHLY
OOP_ANNUAL = HEALTHCARE.OOP_ANNUAL
IRMAA_BRACKETS_SINGLE = MEDICARE.IRMAA_BRACKETS_SINGLE
LTC_FACILITY_MONTHLY = HEALTHCARE.LTC_FACILITY_MONTHLY
LTC_HOME_CARE_MONTHLY = HEALTHCARE.LTC_HOME_CARE_MONTHLY
LTC_DEFAULT_MONTHS_HOME = HEALTHCARE.LTC_DEFAULT_MONTHS_HOME
LTC_DEFAULT_MONTHS_FACILITY = HEALTHCARE.LTC_DEFAULT_MONTHS_FACILITY


def get_irmaa_surcharge(
    annual_income: float,
    filing_status: str = "single",
) -> tuple[float, float]:
    """Get monthly IRMAA surcharges for Part B and Part D.

    Args:
        annual_income: Modified Adjusted Gross Income
        filing_status: 'single' or 'married' (married thresholds are ~2x)

    Returns:
        Tuple of (monthly Part B surcharge, monthly Part D surcharge)
    """
    brackets = IRMAA_BRACKETS_SINGLE
    multiplier = 2.0 if filing_status == "married" else 1.0

    for threshold, part_b, part_d in brackets:
        if annual_income <= threshold * multiplier:
            return (part_b, part_d)

    # Above highest bracket
    last = brackets[-1]
    return (last[1], last[2])


def estimate_annual_healthcare_cost(
    age: int,
    retirement_income: float = 0,
    is_married: bool = False,
    include_ltc: bool = True,
    ltc_start_age: int = 85,
    ltc_duration_years: int = 3,
    current_age: int = 35,
    medical_inflation_rate: float = 6.0,
) -> dict:
    """Estimate annual healthcare costs at a given age.

    Args:
        age: The age to estimate costs for
        retirement_income: Annual income in retirement (for IRMAA calculation)
        is_married: Whether married (affects ACA and IRMAA thresholds)
        include_ltc: Whether to include long-term care costs
        ltc_start_age: Age when LTC costs begin
        ltc_duration_years: How many years of LTC to model
        current_age: Current age (for inflation calculation)
        medical_inflation_rate: Annual medical inflation rate (e.g., 6.0 for 6%)

    Returns:
        Dict with cost breakdown and total annual cost (in today's dollars)
    """
    costs = {
        "aca_insurance": 0.0,
        "medicare_part_b": 0.0,
        "medicare_part_d": 0.0,
        "medigap": 0.0,
        "irmaa_surcharge": 0.0,
        "out_of_pocket": 0.0,
        "long_term_care": 0.0,
        "total": 0.0,
    }

    if age < 65:
        # Pre-Medicare: ACA marketplace
        monthly = ACA_MONTHLY_COUPLE if is_married else ACA_MONTHLY_SINGLE
        costs["aca_insurance"] = monthly * 12
    else:
        # Medicare Part B
        costs["medicare_part_b"] = MEDICARE_PART_B_MONTHLY * 12

        # Medicare Part D
        costs["medicare_part_d"] = MEDICARE_PART_D_MONTHLY * 12

        # Medigap supplement
        costs["medigap"] = MEDIGAP_MONTHLY * 12

        # IRMAA surcharges
        filing = "married" if is_married else "single"
        part_b_surcharge, part_d_surcharge = get_irmaa_surcharge(retirement_income, filing)
        costs["irmaa_surcharge"] = (part_b_surcharge + part_d_surcharge) * 12

    # Out-of-pocket costs (all ages)
    costs["out_of_pocket"] = OOP_ANNUAL

    # Long-term care
    if include_ltc and ltc_start_age <= age < ltc_start_age + ltc_duration_years:
        # Blend of home care and facility care
        years_in_ltc = age - ltc_start_age
        if years_in_ltc < 1:
            # First year: home care
            costs["long_term_care"] = LTC_HOME_CARE_MONTHLY * 12
        else:
            # Subsequent years: facility care
            costs["long_term_care"] = LTC_FACILITY_MONTHLY * 12

    # Sum total in today's dollars (before inflation)
    base_total = sum(costs.values())
    costs["total"] = base_total

    return costs


def estimate_lifetime_healthcare_costs(
    current_age: int,
    retirement_age: int,
    life_expectancy: int,
    retirement_income: float = 50000,
    is_married: bool = False,
    include_ltc: bool = True,
    ltc_start_age: int = 85,
    ltc_duration_years: int = 3,
    medical_inflation_rate: float = 6.0,
) -> dict:
    """Estimate total lifetime healthcare costs from current age to life expectancy.

    Returns a summary with phase totals and year-by-year breakdown.
    """
    yearly_costs = []
    pre_65_total = 0.0
    medicare_total = 0.0
    ltc_total = 0.0

    for age in range(current_age, life_expectancy + 1):
        costs = estimate_annual_healthcare_cost(
            age=age,
            retirement_income=retirement_income,
            is_married=is_married,
            include_ltc=include_ltc,
            ltc_start_age=ltc_start_age,
            ltc_duration_years=ltc_duration_years,
            current_age=current_age,
            medical_inflation_rate=medical_inflation_rate,
        )

        yearly_costs.append({"age": age, **costs})

        if age < 65:
            pre_65_total += costs["total"]
        elif age < ltc_start_age or not include_ltc:
            medicare_total += costs["total"]
        else:
            ltc_total += costs["total"]

    return {
        "pre_65_total": round(pre_65_total, 2),
        "medicare_total": round(medicare_total, 2),
        "ltc_total": round(ltc_total, 2),
        "grand_total": round(pre_65_total + medicare_total + ltc_total, 2),
        "yearly_breakdown": yearly_costs,
    }
