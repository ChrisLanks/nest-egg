"""Centralized financial constants — the ONE file admins update when rules change.

===========================================================================
HOW TO USE
===========================================================================
Import what you need:

    from app.constants.financial import TAX, SS, MEDICARE, RMD, ...

Each section is a plain namespace class so IDE autocomplete works and the
constant's origin is obvious in call-sites.

===========================================================================
TAX YEAR: 2024  (update annually — search "# ANNUAL" for lines to review)
===========================================================================
"""

from decimal import Decimal
from typing import Dict, List, Tuple

# =========================================================================
# TAX RATES & BRACKETS
# =========================================================================


class TAX:
    """Federal and state tax defaults used across services."""

    # Default marginal rates for estimation (not full bracket math)
    FEDERAL_MARGINAL_RATE = Decimal("0.22")  # 22% — median earner  # ANNUAL
    STATE_AVERAGE_RATE = Decimal("0.05")  # 5% average state     # ANNUAL
    COMBINED_RATE = FEDERAL_MARGINAL_RATE + STATE_AVERAGE_RATE

    # Long-term capital gains brackets (2024, single filer)              # ANNUAL
    LTCG_BRACKETS_SINGLE: List[Tuple[float, float]] = [
        (47_025, 0.00),  # 0% up to $47,025 taxable income
        (518_900, 0.15),  # 15% up to $518,900
        (float("inf"), 0.20),  # 20% above $518,900
    ]
    LTCG_BRACKETS_MARRIED: List[Tuple[float, float]] = [
        (94_050, 0.00),  # 0% up to $94,050
        (583_750, 0.15),  # 15% up to $583,750
        (float("inf"), 0.20),
    ]

    # Net Investment Income Tax (Obamacare surtax)
    NII_SURTAX_RATE = 0.038  # 3.8% on investment income above MAGI threshold
    NII_THRESHOLD_SINGLE = 200_000  # ANNUAL
    NII_THRESHOLD_MARRIED = 250_000  # ANNUAL

    # Standard deductions (2024)                                          # ANNUAL
    STANDARD_DEDUCTION_SINGLE = 14_600
    STANDARD_DEDUCTION_MARRIED = 29_200
    STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE = 1_950  # Additional for 65+
    STANDARD_DEDUCTION_OVER_65_EXTRA_MARRIED = 1_550  # Additional per spouse 65+

    # Social Security benefit taxation thresholds (combined income)
    SS_TAXATION_THRESHOLDS_SINGLE: List[Tuple[float, float]] = [
        (25_000, 0.00),  # 0% of SS taxable below $25k
        (34_000, 0.50),  # Up to 50% taxable between $25k-$34k
        (float("inf"), 0.85),  # Up to 85% taxable above $34k
    ]
    SS_TAXATION_THRESHOLDS_MARRIED: List[Tuple[float, float]] = [
        (32_000, 0.00),
        (44_000, 0.50),
        (float("inf"), 0.85),
    ]


# =========================================================================
# RETIREMENT CONTRIBUTION LIMITS
# =========================================================================


class RETIREMENT:
    """IRS contribution limits and retirement planning defaults."""

    # 401(k) / 403(b) / 457(b) limits (2024)                             # ANNUAL
    LIMIT_401K = 23_000
    LIMIT_401K_CATCH_UP = 7_500  # Age 50+ catch-up
    LIMIT_401K_TOTAL = 69_000  # Total (employee + employer)

    # IRA limits (2024)                                                   # ANNUAL
    LIMIT_IRA = 7_000
    LIMIT_IRA_CATCH_UP = 1_000  # Age 50+ catch-up

    # HSA limits (2024)                                                   # ANNUAL
    LIMIT_HSA_INDIVIDUAL = 4_150
    LIMIT_HSA_FAMILY = 8_300
    LIMIT_HSA_CATCH_UP = 1_000  # Age 55+ catch-up

    # SEP IRA (2024)                                                      # ANNUAL
    LIMIT_SEP_IRA = 69_000
    SEP_IRA_COMPENSATION_CAP = 345_000

    # SIMPLE IRA (2024)                                                   # ANNUAL
    LIMIT_SIMPLE_IRA = 16_000
    LIMIT_SIMPLE_IRA_CATCH_UP = 3_500

    # 529 Plan
    LIMIT_529_ANNUAL_GIFT_EXCLUSION = 18_000  # Per beneficiary, per donor  # ANNUAL
    LIMIT_529_SUPERFUND = 90_000  # 5-year gift tax averaging

    # Retirement planning defaults
    DEFAULT_RETIREMENT_AGE = 67
    DEFAULT_LIFE_EXPECTANCY = 95
    SPENDING_RATIO_HOUSEHOLD = 0.85  # 85% of pre-retirement income
    SPENDING_RATIO_SINGLE = 0.80  # 80% of pre-retirement income
    FALLBACK_SPENDING_HOUSEHOLD = 80_000  # If no income data available
    FALLBACK_SPENDING_SINGLE = 60_000

    # Catch-up contribution eligibility ages (IRS rules)         # ANNUAL (watch SECURE 3.0)
    CATCH_UP_AGE_401K = 50  # Age 50+: 401k / 403b / IRA catch-up eligible
    CATCH_UP_AGE_HSA = 55  # Age 55+: HSA catch-up eligible


# =========================================================================
# SOCIAL SECURITY
# =========================================================================


class SS:
    """Social Security parameters (2024)."""

    # PIA bend points (monthly AIME amounts)                              # ANNUAL
    BEND_POINT_1 = 1_174
    BEND_POINT_2 = 7_078

    # Replacement rates at each PIA segment
    RATE_1 = 0.90  # 90% of AIME up to 1st bend point
    RATE_2 = 0.32  # 32% between bend points
    RATE_3 = 0.15  # 15% above 2nd bend point

    # Taxable earnings maximum                                            # ANNUAL
    TAXABLE_MAX = 168_600

    # Wage growth assumption for AIME estimation
    WAGE_GROWTH = 0.025  # 2.5% per year

    # Full Retirement Age table: birth_year → (years, months)
    FRA_TABLE: Dict[int, Tuple[int, int]] = {
        1937: (65, 0),
        1938: (65, 2),
        1939: (65, 4),
        1940: (65, 6),
        1941: (65, 8),
        1942: (65, 10),
        # 1943-1954: FRA = 66 (handled in code)
        1955: (66, 2),
        1956: (66, 4),
        1957: (66, 6),
        1958: (66, 8),
        1959: (66, 10),
        # 1960+: FRA = 67 (handled in code)
    }

    # Early/delayed claiming adjustment rates
    EARLY_REDUCTION_FIRST_36_MO = 5 / 9 / 100  # Per month (≈0.556%)
    EARLY_REDUCTION_BEYOND_36_MO = 5 / 12 / 100  # Per month (≈0.417%)
    DELAYED_CREDIT_PER_MONTH = 2 / 3 / 100  # Per month (≈0.667%)
    MAX_CLAIMING_AGE = 70
    MIN_CLAIMING_AGE = 62

    # Age to start surfacing SS planning advice (2 years before earliest claiming)
    PLANNING_START_AGE = 60


# =========================================================================
# MEDICARE & IRMAA
# =========================================================================


class MEDICARE:
    """Medicare costs and IRMAA brackets (2024)."""

    # Base premiums (monthly)                                             # ANNUAL
    PART_B_MONTHLY = 174.70
    PART_D_MONTHLY = 34.70
    MEDIGAP_MONTHLY = 150.00  # Plan G national average

    # IRMAA brackets (single filer): (MAGI threshold, Part B surcharge, Part D surcharge)
    IRMAA_BRACKETS_SINGLE: List[Tuple[float, float, float]] = [  # ANNUAL
        (103_000, 0.00, 0.00),  # Standard
        (129_000, 70.90, 12.90),  # Tier 1
        (161_000, 161.40, 33.30),  # Tier 2
        (193_000, 251.90, 53.80),  # Tier 3
        (500_000, 342.30, 74.20),  # Tier 4
        (float("inf"), 395.60, 81.00),  # Tier 5
    ]
    # Married thresholds are approximately 2x single (applied via multiplier in code)

    # Medicare eligibility age
    ELIGIBILITY_AGE = 65

    # IRMAA uses income from 2 years prior — start planning 2 years before eligibility
    IRMAA_PLANNING_AGE = 63  # ANNUAL (tied to ELIGIBILITY_AGE)


# =========================================================================
# HEALTHCARE COSTS
# =========================================================================


class HEALTHCARE:
    """Healthcare cost assumptions (2024 dollars)."""

    # Pre-65 ACA marketplace (mid-tier Silver, no subsidies)
    ACA_MONTHLY_SINGLE = 600  # ANNUAL
    ACA_MONTHLY_COUPLE = 1_200

    # Out-of-pocket (dental, vision, copays)
    OOP_ANNUAL = 3_000

    # Long-term care defaults (national medians)
    LTC_FACILITY_MONTHLY = 5_900  # Nursing home semi-private
    LTC_HOME_CARE_MONTHLY = 1_966  # Home health aide
    LTC_DEFAULT_MONTHS_HOME = 12  # Average months home care first
    LTC_DEFAULT_MONTHS_FACILITY = 16  # Average months in facility

    # Medical inflation assumption
    DEFAULT_MEDICAL_INFLATION = 6.0  # Percent per year

    # Long-term care modeling defaults (used when caller supplies no overrides)
    LTC_DEFAULT_START_AGE = 85  # Age at which LTC costs begin
    LTC_DEFAULT_DURATION_YEARS = 3  # Years of LTC to model
    LTC_DEFAULT_RETIREMENT_INCOME = 50_000  # Assumed income for IRMAA estimation
    LTC_DEFAULT_CURRENT_AGE = 35  # Fallback current age when birthdate unknown


# =========================================================================
# RMD (Required Minimum Distributions)
# =========================================================================


class RMD:
    """RMD rules under SECURE 2.0 Act."""

    # Age when RMDs begin  # ANNUAL (watch for SECURE 3.0)
    TRIGGER_AGE = 73

    # Penalty rate for shortfall (reduced from 50% by SECURE 2.0)
    PENALTY_RATE = Decimal("0.25")  # 25%
    PENALTY_RATE_CORRECTED = Decimal("0.10")  # 10% if corrected within 2 years

    # IRS Uniform Lifetime Table (2022+ revision)
    UNIFORM_LIFETIME_TABLE: Dict[int, Decimal] = {
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


# =========================================================================
# EDUCATION PLANNING
# =========================================================================


class EDUCATION:
    """College cost assumptions (2024 dollars, CollegeBoard data)."""

    COLLEGE_COSTS: Dict[str, int] = {  # ANNUAL
        "public_in_state": 23_250,
        "public_out_of_state": 41_000,
        "private": 57_000,
    }
    COLLEGE_INFLATION_RATE = 0.05  # 5% annual college cost inflation
    DEFAULT_ANNUAL_RETURN = 0.06  # 6% expected return for 529
    COLLEGE_YEARS = 4


# =========================================================================
# FIRE / WITHDRAWAL / SIMULATION DEFAULTS
# =========================================================================


class FIRE:
    """FIRE metrics and simulation assumptions."""

    # Safe withdrawal rate
    DEFAULT_WITHDRAWAL_RATE = 0.04  # 4% rule
    FI_MULTIPLIER = 25  # 1 / 0.04

    # Return / inflation assumptions
    DEFAULT_EXPECTED_RETURN = 0.07  # 7% nominal
    DEFAULT_EXPECTED_RETURN_PCT = Decimal("7.00")  # Same as above, in percent form
    DEFAULT_POST_RETIREMENT_RETURN = 0.05  # 5% nominal (conservative)
    DEFAULT_POST_RETIREMENT_RETURN_PCT = Decimal("5.00")
    DEFAULT_INFLATION = 0.03  # 3% general inflation
    DEFAULT_INFLATION_PCT = Decimal("3.00")
    DEFAULT_REAL_RETURN = DEFAULT_EXPECTED_RETURN - DEFAULT_INFLATION  # 4%
    DEFAULT_WITHDRAWAL_RATE_PCT = Decimal("4.00")  # Same as DEFAULT_WITHDRAWAL_RATE
    DEFAULT_CAPITAL_GAINS_RATE = Decimal("0.15")  # 15% — middle LTCG bracket  # ANNUAL
    DEFAULT_CAPITAL_GAINS_RATE_PCT = Decimal("15.00")

    # Monte Carlo defaults
    MC_PRE_RETIREMENT_RETURN = 7.0  # Percent
    MC_POST_RETIREMENT_RETURN = 5.0
    MC_VOLATILITY = 15.0
    MC_INFLATION = 3.0
    MC_DEFAULT_SIMS = 2_500
    MC_QUICK_SIMS = 500

    # Tax rate caps for withdrawal strategy (prevent unreasonable gross-up)
    MAX_CAPITAL_GAINS_RATE = 0.50
    MAX_INCOME_TAX_RATE = 0.70


# =========================================================================
# FINANCIAL HEALTH BENCHMARKS
# =========================================================================


class HEALTH:
    """Financial health scoring thresholds."""

    # Grade cutoffs (overall 0-100 score)
    GRADE_A = 90
    GRADE_B = 75
    GRADE_C = 60
    GRADE_D = 40

    # Savings rate thresholds
    SAVINGS_RATE_EXCELLENT = 20  # Percent → score 100
    SAVINGS_RATE_GOOD = 10  # Percent → score 50

    # Emergency fund thresholds (months of expenses)
    EMERGENCY_FUND_EXCELLENT = 6  # Months → score 100
    EMERGENCY_FUND_GOOD = 3  # Months → score 50

    # Debt-to-income thresholds
    DTI_EXCELLENT = 15  # Percent → score 100
    DTI_FAIR = 35  # Percent → score 50
    DTI_UPPER_BOUND = 50  # Percent → score 0 (above this = worst tier)

    # Fidelity retirement benchmarks (age → multiples of salary)
    RETIREMENT_BENCHMARKS: List[Tuple[int, int]] = [
        (30, 1),
        (40, 3),
        (50, 6),
        (60, 8),
    ]

    # Interpolation boundary ages for retirement benchmark
    RETIREMENT_BENCHMARK_MIN_AGE = 30
    RETIREMENT_BENCHMARK_MAX_AGE = 60
    RETIREMENT_BENCHMARK_MIN_MULT = 1
    RETIREMENT_BENCHMARK_MAX_MULT = 8

    # Retirement progress scoring bands (score = highest band where progress >= band)
    RETIREMENT_SCORE_BAND_HIGH = 75.0  # Progress >= 75% → score 75
    RETIREMENT_SCORE_BAND_LOW = 25.0  # Progress >= 25% → score 25


# =========================================================================
# PORTFOLIO PRESETS
# =========================================================================


class PORTFOLIO:
    """Preset portfolio allocations."""

    PRESETS: Dict[str, Dict] = {
        "bogleheads_3fund": {
            "name": "Bogleheads Three-Fund Portfolio",
            "allocations": [
                {"asset_class": "domestic", "target_percent": 60, "label": "US Stocks"},
                {
                    "asset_class": "international",
                    "target_percent": 30,
                    "label": "International Stocks",
                },
                {"asset_class": "bond", "target_percent": 10, "label": "Bonds"},
            ],
        },
        "balanced_60_40": {
            "name": "Balanced 60/40 Portfolio",
            "allocations": [
                {"asset_class": "domestic", "target_percent": 42, "label": "US Stocks"},
                {
                    "asset_class": "international",
                    "target_percent": 18,
                    "label": "International Stocks",
                },
                {"asset_class": "bond", "target_percent": 40, "label": "Bonds"},
            ],
        },
        "target_date_2050": {
            "name": "Target Date 2050",
            "allocations": [
                {"asset_class": "domestic", "target_percent": 54, "label": "US Stocks"},
                {
                    "asset_class": "international",
                    "target_percent": 36,
                    "label": "International Stocks",
                },
                {"asset_class": "bond", "target_percent": 10, "label": "Bonds"},
            ],
        },
        "conservative_30_70": {
            "name": "Conservative 30/70 Portfolio",
            "allocations": [
                {"asset_class": "domestic", "target_percent": 21, "label": "US Stocks"},
                {
                    "asset_class": "international",
                    "target_percent": 9,
                    "label": "International Stocks",
                },
                {"asset_class": "bond", "target_percent": 60, "label": "Bonds"},
                {"asset_class": "cash", "target_percent": 10, "label": "Cash"},
            ],
        },
        "all_weather": {
            "name": "All Weather Portfolio",
            "allocations": [
                {"asset_class": "domestic", "target_percent": 30, "label": "US Stocks"},
                {"asset_class": "bond", "target_percent": 55, "label": "Bonds"},
                {"asset_class": "other", "target_percent": 15, "label": "Alternatives"},
            ],
        },
    }


# =========================================================================
# LIFE EVENT COST DEFAULTS
# =========================================================================


class LIFE_EVENTS:
    """Default costs for life event presets (2024 dollars)."""

    # Children
    DAYCARE_ANNUAL = Decimal("15000")
    DAYCARE_YEARS = 5
    ACTIVITIES_ANNUAL = Decimal("5000")
    ACTIVITIES_YEARS = 13
    COLLEGE_PUBLIC_ANNUAL = Decimal("25000")
    COLLEGE_PRIVATE_ANNUAL = Decimal("60000")
    COLLEGE_YEARS = 4

    # Pets
    DOG_ANNUAL = Decimal("3000")
    DOG_LIFESPAN = 12
    CAT_ANNUAL = Decimal("1500")
    CAT_LIFESPAN = 15

    # Home
    HOME_PURCHASE_COST = Decimal("100000")
    HOME_RENOVATION_COST = Decimal("50000")
    HOME_DOWNSIZE_PROCEEDS = Decimal("150000")

    # Career
    SABBATICAL_INCOME_LOSS = Decimal("-50000")
    RAISE_INCOME_GAIN = Decimal("20000")
    BONUS_AMOUNT = Decimal("50000")

    # Healthcare
    PRE_65_INSURANCE_ANNUAL = Decimal("7200")
    LTC_ANNUAL = Decimal("60000")
    LTC_YEARS = 3
    MAJOR_PROCEDURE = Decimal("15000")

    # Travel
    TRAVEL_MODERATE_ANNUAL = Decimal("10000")
    TRAVEL_PREMIUM_ANNUAL = Decimal("25000")

    # Vehicles
    VEHICLE_PURCHASE = Decimal("35000")
    VEHICLE_ANNUAL = Decimal("5000")

    # Elder care
    ELDER_CARE_ANNUAL = Decimal("25000")
    ELDER_CARE_YEARS = 5


# =========================================================================
# DEBT PAYOFF DEFAULTS
# =========================================================================


class DEBT:
    """Default assumptions for debt payoff calculations."""

    # Credit card minimum payment
    MIN_PAYMENT_RATE = Decimal("0.02")  # 2% of balance
    MIN_PAYMENT_FLOOR = Decimal("25.00")  # $25 minimum floor

    # Fallback interest rate when the account has no rate set
    DEFAULT_INTEREST_RATE = Decimal("18.0")  # 18% — typical credit card APR  # ANNUAL

    # Payoff horizon defaults
    DEFAULT_PAYOFF_MONTHS = 60  # 5-year assumed payoff for unknown loan terms
    MAX_PAYOFF_MONTHS = 360  # 30-year hard cap on all simulations


# =========================================================================
# CAREER / EARNINGS ASSUMPTIONS
# =========================================================================


class CAREER:
    """Career and earnings assumptions used in Social Security projections."""

    DEFAULT_START_AGE = 22  # Assumed career start when not provided
    SS_TOP_EARNINGS_YEARS = 35  # IRS uses highest 35 years for AIME calculation
    DEFAULT_CURRENT_AGE = 35  # Fallback current age when birthdate is unavailable


# =========================================================================
# SAVINGS GOAL TEMPLATE DEFAULTS
# =========================================================================


class SAVINGS_GOALS:
    """Default amounts for pre-built savings goal templates (2024 dollars)."""

    # Emergency fund: fallback monthly expense assumption when no tx history
    DEFAULT_MONTHLY_EXPENSES = Decimal("3000")  # ANNUAL (median US household)

    # Vacation fund template target
    VACATION_TARGET = Decimal("4000")  # ANNUAL

    # Home down payment template (20% of ~$300K median US home price)
    HOME_DOWN_PAYMENT = Decimal("60000")  # ANNUAL

    # Debt payoff reserve: fraction of total debt to set aside
    DEBT_PAYOFF_RESERVE_RATE = Decimal("0.10")  # 10% of total debt
    DEBT_PAYOFF_RESERVE_MIN = Decimal("1000")  # Minimum reserve regardless of debt size
