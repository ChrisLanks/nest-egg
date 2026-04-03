"""Centralized financial constants — the ONE file admins update when rules change.

===========================================================================
HOW TO USE
===========================================================================
Import what you need:

    from app.constants.financial import TAX, SS, MEDICARE, RMD, ...

Each section is a plain namespace class so IDE autocomplete works and the
constant's origin is obvious in call-sites.

===========================================================================
ANNUAL DATA UPDATES
===========================================================================
IRS publishes new limits each October/November for the following tax year.
When that happens, add a new dict entry to the appropriate _*_DATA table
below — that's the ONLY change needed.

If no entry exists for the current year, the projection engine automatically
estimates values by applying per-field COLA rates (see _*_PROJ dicts) from
the most recent known anchor year.  Hardcoded years always win over projected
values, so adding an exact entry for a future year overrides any estimate.

YTD resets are handled dynamically in services (date-based), not here.
===========================================================================
TRIENNIAL DATA UPDATES (every 3 years)
===========================================================================
NET_WORTH_BENCHMARKS — Federal Reserve Survey of Consumer Finances (SCF)
The Fed releases new SCF data every 3 years (2022, 2025, 2028 …).

  Automated:  python -m app.services.scf_benchmark_service --scrape
              Updates NET_WORTH_BENCHMARKS and writes backend/app/constants/scf_cache.json

  Manual:     See the large comment block above the NET_WORTH_BENCHMARKS
              class at the bottom of this file.

The UI automatically shows a "Data as of YYYY — update in progress" notice
when SURVEY_YEAR is more than 3 years old.
===========================================================================
ADJACENT CONSTANTS FILE
===========================================================================
app/constants/state_tax_rates.py lives alongside this file and contains
state income tax rates (STATE_TAX_RATES dict, keyed by two-letter state
code).  It is kept separate because state rates change on a different
cadence than federal limits — some states update mid-year.  When state
rates change, edit that file only; nothing here needs updating.

    from app.constants.state_tax_rates import STATE_TAX_RATES
===========================================================================
"""

import datetime
from decimal import Decimal
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _best_year(table: dict, year: int | None = None) -> int:
    """Return the closest known year ≤ requested year (fallback: earliest known).

    Examples:
        _best_year({2024: ..., 2026: ...}, 2025)  → 2024
        _best_year({2024: ..., 2026: ...}, 2026)  → 2026
        _best_year({2024: ..., 2026: ...}, 2023)  → 2024  (no older — use earliest)
    """
    y = year if year is not None else datetime.date.today().year
    candidates = sorted(table, reverse=True)
    for k in candidates:
        if k <= y:
            return k
    return candidates[-1]  # all known years are ahead of y — return earliest


def _project(base: dict, years: int, rules: dict) -> dict:
    """Extrapolate `base` forward by `years` using per-field COLA rules.

    rules format — two variants per field:
      (rate, rnd)            — scalar or bracket-threshold-only scaling
      [(r0,rnd0),(r1,rnd1)]  — per-position scaling for bracket lists

    rate=0.0 → fixed by law (value unchanged).
    rnd=0    → float result (no integer rounding).
    rnd<1    → round to nearest rnd (e.g. 0.10 for cents).
    rnd≥1    → round to nearest integer multiple of rnd.

    For list-of-tuple fields with a plain (rate, rnd) rule, only position-0
    (the income/dollar threshold) is scaled; other positions are kept as-is.
    """
    if years <= 0:
        return dict(base)

    def _scale(v: float, rate: float, rnd: float) -> float:
        if rate == 0.0:
            return v
        projected = v * (1 + rate) ** years
        if not rnd:
            return round(projected, 2)
        rounded = round(projected / rnd) * rnd
        return int(rounded) if rnd >= 1 else round(rounded, 2)

    result = {}
    for field, value in base.items():
        rule = rules.get(field)
        if rule is None:
            result[field] = value
        elif isinstance(value, list):
            new_list = []
            for item in value:
                if not isinstance(item, tuple):
                    new_list.append(item)
                    continue
                new_item = []
                for i, v in enumerate(item):
                    if v == float("inf"):
                        new_item.append(v)
                        continue
                    # Per-position list rule or default (scale threshold only)
                    if isinstance(rule, list):
                        pos_rule = rule[i] if i < len(rule) else (0.0, 0)
                    else:
                        pos_rule = rule if i == 0 else (0.0, 0)
                    new_item.append(_scale(v, pos_rule[0], pos_rule[1]))
                new_list.append(tuple(new_item))
            result[field] = new_list
        else:
            r, rnd = rule if isinstance(rule, tuple) else (rule, 0)
            result[field] = _scale(value, r, rnd)
    return result


def _resolve(table: dict, rules: dict, year: int | None = None) -> dict:
    """Return data for `year`, projecting forward from the closest anchor if needed.

    If `year` is exactly in `table`, returns that entry unchanged.
    Otherwise, projects forward from the closest known year ≤ `year`.
    """
    y = year if year is not None else datetime.date.today().year
    anchor = _best_year(table, y)
    return _project(table[anchor], y - anchor, rules)


# ===========================================================================
# PER-YEAR IRS DATA
# Add a new dict entry each November when IRS announces the next year's limits.
# ===========================================================================

_RETIREMENT_LIMITS: dict[int, dict] = {
    2024: {
        "LIMIT_401K": 23_000,
        "LIMIT_401K_CATCH_UP": 7_500,
        "LIMIT_401K_SUPER_CATCH_UP": 0,  # SECURE 2.0 super catch-up starts 2025
        "LIMIT_401K_TOTAL": 69_000,
        "LIMIT_IRA": 7_000,
        "LIMIT_IRA_CATCH_UP": 1_000,
        "LIMIT_HSA_INDIVIDUAL": 4_150,
        "LIMIT_HSA_FAMILY": 8_300,
        "LIMIT_HSA_CATCH_UP": 1_000,
        "LIMIT_SEP_IRA": 69_000,
        "SEP_IRA_COMPENSATION_CAP": 345_000,
        "LIMIT_SIMPLE_IRA": 16_000,
        "LIMIT_SIMPLE_IRA_CATCH_UP": 3_500,
        "LIMIT_529_ANNUAL_GIFT_EXCLUSION": 18_000,
        "LIMIT_529_SUPERFUND": 90_000,
    },
    2025: {
        "LIMIT_401K": 23_500,
        "LIMIT_401K_CATCH_UP": 7_500,
        "LIMIT_401K_SUPER_CATCH_UP": 11_250,  # SECURE 2.0: ages 60-63
        "LIMIT_401K_TOTAL": 70_000,
        "LIMIT_IRA": 7_000,
        "LIMIT_IRA_CATCH_UP": 1_000,
        "LIMIT_HSA_INDIVIDUAL": 4_300,
        "LIMIT_HSA_FAMILY": 8_550,
        "LIMIT_HSA_CATCH_UP": 1_000,
        "LIMIT_SEP_IRA": 70_000,
        "SEP_IRA_COMPENSATION_CAP": 350_000,
        "LIMIT_SIMPLE_IRA": 16_500,
        "LIMIT_SIMPLE_IRA_CATCH_UP": 3_500,
        "LIMIT_529_ANNUAL_GIFT_EXCLUSION": 19_000,
        "LIMIT_529_SUPERFUND": 95_000,
    },
    2026: {
        # Source: IRS Notice 2025-67, IRS.gov newsroom (Oct 2025)
        "LIMIT_401K": 24_500,  # IRS confirmed
        "LIMIT_401K_CATCH_UP": 8_000,  # Age 50+ catch-up; IRS confirmed
        "LIMIT_401K_SUPER_CATCH_UP": 12_000,  # SECURE 2.0: ages 60-63; IRS confirmed (1.5x catch-up)
        "LIMIT_401K_TOTAL": 70_000,  # Section 415(c) total (employee + employer); IRS confirmed
        "LIMIT_IRA": 7_500,  # IRS confirmed
        "LIMIT_IRA_CATCH_UP": 1_100,  # Age 50+; IRS confirmed (increased from $1,000)
        "LIMIT_HSA_INDIVIDUAL": 4_400,  # IRS confirmed
        "LIMIT_HSA_FAMILY": 8_750,  # IRS confirmed
        "LIMIT_HSA_CATCH_UP": 1_000,  # Age 55+ (unchanged)
        "LIMIT_SEP_IRA": 70_000,  # IRS confirmed (same as 415(c) limit)
        "SEP_IRA_COMPENSATION_CAP": 360_000,  # IRS confirmed
        "LIMIT_SIMPLE_IRA": 17_000,  # IRS confirmed
        "LIMIT_SIMPLE_IRA_CATCH_UP": 4_000,  # Age 50+ catch-up; IRS confirmed
        "LIMIT_529_ANNUAL_GIFT_EXCLUSION": 19_000,  # Unchanged from 2025; IRS confirmed
        "LIMIT_529_SUPERFUND": 95_000,  # 5 × gift exclusion; unchanged from 2025
    },
}

# COLA projection rules for retirement limits.
# Format: (annual_rate, round_to_nearest) — round_to=0 means float, rate=0.0 means fixed.
_RETIREMENT_PROJ: dict[str, tuple] = {
    "LIMIT_401K": (0.025, 500),  # IRS CPI-W indexed, $500 increments
    "LIMIT_401K_CATCH_UP": (0.025, 500),
    "LIMIT_401K_SUPER_CATCH_UP": (0.025, 500),  # SECURE 2.0: ages 60-63
    "LIMIT_401K_TOTAL": (0.025, 1_000),  # Section 415(c) total
    "LIMIT_IRA": (0.025, 500),
    "LIMIT_IRA_CATCH_UP": (0.025, 100),
    "LIMIT_HSA_INDIVIDUAL": (0.030, 50),  # CPI (all items), $50 increments
    "LIMIT_HSA_FAMILY": (0.030, 50),
    "LIMIT_HSA_CATCH_UP": (0.00, 0),  # Fixed at $1,000 by statute
    "LIMIT_SEP_IRA": (0.025, 1_000),
    "SEP_IRA_COMPENSATION_CAP": (0.025, 5_000),
    "LIMIT_SIMPLE_IRA": (0.025, 500),
    "LIMIT_SIMPLE_IRA_CATCH_UP": (0.025, 500),
    "LIMIT_529_ANNUAL_GIFT_EXCLUSION": (0.025, 1_000),
    "LIMIT_529_SUPERFUND": (0.025, 5_000),  # Always 5× gift exclusion
}

_TAX_DATA: dict[int, dict] = {
    2024: {
        "STANDARD_DEDUCTION_SINGLE": 14_600,
        "STANDARD_DEDUCTION_MARRIED": 29_200,
        "STANDARD_DEDUCTION_HOH": 21_900,
        "STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE": 1_950,
        "STANDARD_DEDUCTION_OVER_65_EXTRA_MARRIED": 1_550,
        # Ordinary income brackets: list of (rate, ceiling) — ceiling is top of bracket
        "BRACKETS_SINGLE": [
            (0.10, 11_600),
            (0.12, 47_150),
            (0.22, 100_525),
            (0.24, 191_950),
            (0.32, 243_725),
            (0.35, 609_350),
            (0.37, float("inf")),
        ],
        "BRACKETS_MARRIED": [
            (0.10, 23_200),
            (0.12, 94_300),
            (0.22, 201_050),
            (0.24, 383_900),
            (0.32, 487_450),
            (0.35, 731_200),
            (0.37, float("inf")),
        ],
        "BRACKETS_HOH": [
            (0.10, 16_550),
            (0.12, 63_100),
            (0.22, 100_500),
            (0.24, 191_950),
            (0.32, 243_700),
            (0.35, 609_350),
            (0.37, float("inf")),
        ],
        "LTCG_BRACKETS_SINGLE": [
            (47_025, 0.00),
            (518_900, 0.15),
            (float("inf"), 0.20),
        ],
        "LTCG_BRACKETS_MARRIED": [
            (94_050, 0.00),
            (583_750, 0.15),
            (float("inf"), 0.20),
        ],
    },
    2025: {
        "STANDARD_DEDUCTION_SINGLE": 15_000,
        "STANDARD_DEDUCTION_MARRIED": 30_000,
        "STANDARD_DEDUCTION_HOH": 22_500,
        "STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE": 2_000,
        "STANDARD_DEDUCTION_OVER_65_EXTRA_MARRIED": 1_600,
        "BRACKETS_SINGLE": [
            (0.10, 11_925),
            (0.12, 48_475),
            (0.22, 103_350),
            (0.24, 197_300),
            (0.32, 250_525),
            (0.35, 626_350),
            (0.37, float("inf")),
        ],
        "BRACKETS_MARRIED": [
            (0.10, 23_850),
            (0.12, 96_950),
            (0.22, 206_700),
            (0.24, 394_600),
            (0.32, 501_050),
            (0.35, 751_600),
            (0.37, float("inf")),
        ],
        "BRACKETS_HOH": [
            (0.10, 17_000),   # IRS-confirmed 2025 HoH brackets
            (0.12, 64_850),
            (0.22, 103_350),
            (0.24, 197_300),
            (0.32, 250_500),
            (0.35, 626_350),
            (0.37, float("inf")),
        ],
        "LTCG_BRACKETS_SINGLE": [
            (48_350, 0.00),
            (533_400, 0.15),
            (float("inf"), 0.20),
        ],
        "LTCG_BRACKETS_MARRIED": [
            (96_700, 0.00),
            (600_050, 0.15),
            (float("inf"), 0.20),
        ],
    },
    2026: {
        # Source: IRS Rev. Proc. 2025-32 / IRS newsroom (Oct 2025), includes OBBBA amendments
        "STANDARD_DEDUCTION_SINGLE": 16_100,  # IRS confirmed
        "STANDARD_DEDUCTION_MARRIED": 32_200,  # IRS confirmed
        "STANDARD_DEDUCTION_HOH": 24_150,  # Projected from 2025 (~3% inflation)
        "STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE": 2_100,  # Inflation-adjusted estimate
        "STANDARD_DEDUCTION_OVER_65_EXTRA_MARRIED": 1_700,  # Inflation-adjusted estimate
        "BRACKETS_SINGLE": [
            (0.10, 12_300),   # IRS Rev. Proc. 2025-32
            (0.12, 49_950),
            (0.22, 106_550),
            (0.24, 203_350),
            (0.32, 258_250),
            (0.35, 645_850),
            (0.37, float("inf")),
        ],
        "BRACKETS_MARRIED": [
            (0.10, 24_600),
            (0.12, 99_900),
            (0.22, 213_100),
            (0.24, 406_700),
            (0.32, 516_500),
            (0.35, 775_100),
            (0.37, float("inf")),
        ],
        "BRACKETS_HOH": [
            (0.10, 17_050),  # Projected ~3% from 2025
            (0.12, 65_000),
            (0.22, 103_500),
            (0.24, 197_700),
            (0.32, 251_000),
            (0.35, 627_650),
            (0.37, float("inf")),
        ],
        "LTCG_BRACKETS_SINGLE": [
            (49_450, 0.00),  # 0% up to $49,450; IRS confirmed
            (545_500, 0.15),  # 15% up to $545,500; IRS confirmed
            (float("inf"), 0.20),
        ],
        "LTCG_BRACKETS_MARRIED": [
            (98_900, 0.00),  # 0% up to $98,900; IRS confirmed
            (613_700, 0.15),  # 15% up to $613,700; IRS confirmed
            (float("inf"), 0.20),
        ],
    },
}

# COLA projection rules for tax data.
_TAX_PROJ: dict[str, tuple] = {
    "STANDARD_DEDUCTION_SINGLE": (0.025, 50),
    "STANDARD_DEDUCTION_MARRIED": (0.025, 50),
    "STANDARD_DEDUCTION_HOH": (0.025, 50),
    "STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE": (0.025, 50),
    "STANDARD_DEDUCTION_OVER_65_EXTRA_MARRIED": (0.025, 50),
    # Ordinary brackets: scale income thresholds (pos 0) by CPI-W ~2.5%; rates (pos 1) fixed
    "BRACKETS_SINGLE": (0.025, 25),
    "BRACKETS_MARRIED": (0.025, 25),
    "BRACKETS_HOH": (0.025, 25),
    "LTCG_BRACKETS_SINGLE": (0.025, 50),  # Scales income thresholds; rates unchanged
    "LTCG_BRACKETS_MARRIED": (0.025, 50),
}

_SS_DATA: dict[int, dict] = {
    2024: {
        "TAXABLE_MAX": 168_600,
        "BEND_POINT_1": 1_174,
        "BEND_POINT_2": 7_078,
    },
    2025: {
        "TAXABLE_MAX": 176_100,
        "BEND_POINT_1": 1_226,
        "BEND_POINT_2": 7_391,
    },
    2026: {
        # Source: SSA.gov COLA announcement (Oct 2025)
        "TAXABLE_MAX": 184_500,  # SSA confirmed
        "BEND_POINT_1": 1_286,  # SSA confirmed
        "BEND_POINT_2": 7_749,  # SSA confirmed
    },
}

# COLA projection rules for Social Security.
# AWI (National Average Wage Index) historically ~3.5%/yr.
_SS_PROJ: dict[str, tuple] = {
    "TAXABLE_MAX": (0.035, 300),  # AWI-indexed; $300 increments
    "BEND_POINT_1": (0.035, 1),  # AWI-indexed
    "BEND_POINT_2": (0.035, 1),  # AWI-indexed
}

_MEDICARE_DATA: dict[int, dict] = {
    2024: {
        "PART_B_MONTHLY": 174.70,
        "PART_D_MONTHLY": 34.70,
        "IRMAA_BRACKETS_SINGLE": [
            (103_000, 0.00, 0.00),
            (129_000, 70.90, 12.90),
            (161_000, 161.40, 33.30),
            (193_000, 251.90, 53.80),
            (500_000, 342.30, 74.20),
            (float("inf"), 395.60, 81.00),
        ],
        "IRMAA_BRACKETS_MARRIED": [
            (206_000, 0.00, 0.00),
            (258_000, 70.90, 12.90),
            (322_000, 161.40, 33.30),
            (386_000, 251.90, 53.80),
            (750_000, 342.30, 74.20),
            (float("inf"), 395.60, 81.00),
        ],
    },
    2025: {
        "PART_B_MONTHLY": 185.00,
        "PART_D_MONTHLY": 36.78,  # Verify with CMS at cms.gov annually
        "IRMAA_BRACKETS_SINGLE": [
            (106_000, 0.00, 0.00),
            (133_000, 74.00, 13.70),
            (167_000, 185.00, 35.30),
            (200_000, 295.90, 57.00),
            (500_000, 406.90, 78.60),
            (float("inf"), 443.30, 85.80),
        ],
        "IRMAA_BRACKETS_MARRIED": [
            (212_000, 0.00, 0.00),
            (266_000, 74.00, 13.70),
            (334_000, 185.00, 35.30),
            (400_000, 295.90, 57.00),
            (750_000, 406.90, 78.60),
            (float("inf"), 443.30, 85.80),
        ],
    },
    2026: {
        # Source: CMS.gov Medicare announcement (Oct 2025)
        # IRMAA based on 2024 MAGI; Part B surcharges use CMS multiplier model
        # Multipliers: 1.4×, 2.0×, 2.6×, 3.2×, 3.4× base Part B premium
        "PART_B_MONTHLY": 202.90,  # CMS confirmed
        "PART_D_MONTHLY": 40.00,  # Estimated; verify with CMS at cms.gov annually
        "IRMAA_BRACKETS_SINGLE": [
            (109_000, 0.00, 0.00),  # Standard — no surcharge; confirmed
            (137_000, 81.20, 14.50),  # Tier 1 (1.4×); confirmed
            (172_000, 202.90, 37.40),  # Tier 2 (2.0×); Part D estimated
            (205_000, 324.60, 60.30),  # Tier 3 (2.6×); Part D estimated
            (500_000, 446.40, 83.20),  # Tier 4 (3.2×); Part D estimated
            (float("inf"), 487.00, 91.00),  # Tier 5 (3.4×); confirmed
        ],
        "IRMAA_BRACKETS_MARRIED": [
            (218_000, 0.00, 0.00),  # Standard — no surcharge
            (274_000, 81.20, 14.50),  # Tier 1
            (344_000, 202.90, 37.40),  # Tier 2
            (410_000, 324.60, 60.30),  # Tier 3
            (750_000, 446.40, 83.20),  # Tier 4
            (float("inf"), 487.00, 91.00),  # Tier 5
        ],
    },
}

# COLA projection rules for Medicare.
# IRMAA bracket tuples: (income_threshold, part_b_surcharge, part_d_surcharge)
# Per-position rules: threshold→CPI 3%, Part B surcharge→5%, Part D surcharge→4%
_MEDICARE_PROJ: dict[str, object] = {
    "PART_B_MONTHLY": (0.05, 0.10),  # ~5% avg growth; round to nearest $0.10
    "PART_D_MONTHLY": (0.04, 0.10),
    "IRMAA_BRACKETS_SINGLE": [
        (0.030, 1_000),  # income threshold: CPI ~3%, round to $1k
        (0.050, 0.10),  # Part B surcharge: tracks Part B growth ~5%
        (0.040, 0.10),  # Part D surcharge: tracks Part D growth ~4%
    ],
    "IRMAA_BRACKETS_MARRIED": [
        (0.030, 1_000),
        (0.050, 0.10),
        (0.040, 0.10),
    ],
}


# =========================================================================
# TAX RATES & BRACKETS
# =========================================================================


class TAX:
    """Federal and state tax defaults used across services."""

    # Default marginal rates for estimation (not full bracket math)
    FEDERAL_MARGINAL_RATE = Decimal("0.22")  # 22% — median earner
    STATE_AVERAGE_RATE = Decimal("0.05")  # 5% average state
    COMBINED_RATE = FEDERAL_MARGINAL_RATE + STATE_AVERAGE_RATE

    # ── Inflation-adjusted — auto-selected for current tax year ──
    TAX_YEAR = datetime.date.today().year
    _d = _resolve(_TAX_DATA, _TAX_PROJ)

    STANDARD_DEDUCTION_SINGLE = _d["STANDARD_DEDUCTION_SINGLE"]
    STANDARD_DEDUCTION_MARRIED = _d["STANDARD_DEDUCTION_MARRIED"]
    STANDARD_DEDUCTION_HOH = _d.get("STANDARD_DEDUCTION_HOH", _d["STANDARD_DEDUCTION_SINGLE"])
    STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE = _d["STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE"]
    STANDARD_DEDUCTION_OVER_65_EXTRA_MARRIED = _d["STANDARD_DEDUCTION_OVER_65_EXTRA_MARRIED"]
    # Ordinary income brackets for current tax year (COLA-projected if year not in table)
    BRACKETS_SINGLE: List[Tuple[float, float]] = _d["BRACKETS_SINGLE"]
    BRACKETS_MARRIED: List[Tuple[float, float]] = _d["BRACKETS_MARRIED"]
    BRACKETS_HOH: List[Tuple[float, float]] = _d.get("BRACKETS_HOH", _d["BRACKETS_SINGLE"])
    LTCG_BRACKETS_SINGLE: List[Tuple[float, float]] = _d["LTCG_BRACKETS_SINGLE"]
    LTCG_BRACKETS_MARRIED: List[Tuple[float, float]] = _d["LTCG_BRACKETS_MARRIED"]

    # Medical expense deduction floor — IRC §213(a): only expenses exceeding
    # 7.5% of AGI are deductible (permanently set at 7.5% by the 2017 TCJA).
    MEDICAL_DEDUCTION_AGI_FLOOR = Decimal("0.075")

    # Net Investment Income Tax (Obamacare surtax) — thresholds not indexed for inflation
    NII_SURTAX_RATE = 0.038  # 3.8% on investment income above MAGI threshold
    NII_THRESHOLD_SINGLE = 200_000
    NII_THRESHOLD_MARRIED = 250_000

    # Additional Medicare Tax (0.9% surtax) — thresholds not indexed for inflation
    ADDITIONAL_MEDICARE_THRESHOLD_SINGLE = 200_000
    ADDITIONAL_MEDICARE_THRESHOLD_MARRIED = 250_000
    ADDITIONAL_MEDICARE_RATE = Decimal("0.009")

    # SALT cap — year-keyed data (OBBBA 2025 raised cap to $40K for 2025-2028)
    _SALT_CAP_DATA: Dict[int, Dict] = {
        2024: {"cap": 10_000, "phaseout_start": None},
        2025: {"cap": 40_000, "phaseout_start": 500_000},
        2026: {"cap": 40_000, "phaseout_start": 500_000},
        2027: {"cap": 40_000, "phaseout_start": 500_000},
        2028: {"cap": 40_000, "phaseout_start": 500_000},
    }

    @classmethod
    def salt_cap_for_year(cls, year: int | None = None) -> int:
        """Return the SALT cap for the given year."""
        y = year if year is not None else datetime.date.today().year
        entry = cls._SALT_CAP_DATA.get(y)
        if entry:
            return entry["cap"]
        # For years beyond table, assume reverts to $10K (TCJA default)
        return 10_000

    @classmethod
    def salt_cap_phaseout_for_year(cls, year: int | None = None) -> int | None:
        """Return the SALT cap AGI phase-out start for the given year, or None."""
        y = year if year is not None else datetime.date.today().year
        entry = cls._SALT_CAP_DATA.get(y)
        if entry:
            return entry["phaseout_start"]
        return None

    # Convenience current-year properties
    SALT_CAP = _SALT_CAP_DATA[datetime.date.today().year]["cap"] if datetime.date.today().year in _SALT_CAP_DATA else 10_000
    SALT_CAP_PHASEOUT = _SALT_CAP_DATA[datetime.date.today().year]["phaseout_start"] if datetime.date.today().year in _SALT_CAP_DATA else None

    # Social Security benefit taxation thresholds — not indexed for inflation
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

    # Roth IRA income phase-out ranges (year-keyed)
    # COLA ~3.2% (2024→2025), ~3.3% (2025→2026); projected forward at ~3% per year
    _ROTH_PHASEOUT_DATA: Dict[int, Dict] = {
        2024: {"single": (146_000, 161_000), "married": (230_000, 240_000)},
        2025: {"single": (150_000, 165_000), "married": (236_000, 246_000)},
        2026: {"single": (155_000, 170_000), "married": (242_000, 252_000)},
    }
    # COLA projection for years beyond the table (applied to 2026 base)
    _ROTH_PHASEOUT_COLA = 0.03  # ~3% annual COLA
    _ROTH_PHASEOUT_ROUND = 1_000  # IRS rounds to nearest $1,000

    @classmethod
    def roth_phaseout(cls, filing_status: str = "single", year: int | None = None) -> tuple:
        """Return (start, end) Roth IRA phase-out for filing_status and year.

        For years beyond the last hardcoded entry, projects forward using the
        historical COLA rate (~3% per year) rounded to the nearest $1,000 per
        IRS rounding convention.
        """
        y = year if year is not None else datetime.date.today().year
        anchor = _best_year(cls._ROTH_PHASEOUT_DATA, y)
        data = cls._ROTH_PHASEOUT_DATA[anchor]
        key = "married" if filing_status.lower() in ("married", "mfj") else "single"
        start, end = data[key]
        if y > anchor:
            # Project forward from anchor year
            factor = (1 + cls._ROTH_PHASEOUT_COLA) ** (y - anchor)
            r = cls._ROTH_PHASEOUT_ROUND
            start = round(start * factor / r) * r
            end = round(end * factor / r) * r
        return (start, end)

    @classmethod
    def for_year(cls, year: int) -> dict:
        """Return tax constants for a specific year (projects forward if year not hardcoded)."""
        return _resolve(_TAX_DATA, _TAX_PROJ, year)


# =========================================================================
# FICA (Federal Insurance Contributions Act)
# =========================================================================


class FICA:
    """FICA payroll tax rates — statutory constants (not inflation-indexed)."""

    SS_EMPLOYEE_RATE = Decimal("0.062")
    SS_EMPLOYER_RATE = Decimal("0.062")
    SS_SELF_EMPLOYED_RATE = Decimal("0.124")  # Both halves (employee + employer)
    MEDICARE_EMPLOYEE_RATE = Decimal("0.0145")
    MEDICARE_EMPLOYER_RATE = Decimal("0.0145")
    MEDICARE_SELF_EMPLOYED_RATE = Decimal("0.029")  # Both halves
    ADDITIONAL_MEDICARE_RATE = Decimal("0.009")  # 0.9% above threshold
    # Combined employee share: SS (6.2%) + Medicare (1.45%) = 7.65%
    # Unchanged by law; only the SS wage base is inflation-adjusted.
    COMBINED_EMPLOYEE_RATE = Decimal("0.0765")


# =========================================================================
# RETIREMENT CONTRIBUTION LIMITS
# =========================================================================


class RETIREMENT:
    """IRS contribution limits and retirement planning defaults."""

    # ── Inflation-adjusted limits — auto-selected for current tax year ──
    TAX_YEAR = datetime.date.today().year
    _d = _resolve(_RETIREMENT_LIMITS, _RETIREMENT_PROJ)

    LIMIT_401K = _d["LIMIT_401K"]
    LIMIT_401K_CATCH_UP = _d["LIMIT_401K_CATCH_UP"]
    LIMIT_401K_SUPER_CATCH_UP = _d.get("LIMIT_401K_SUPER_CATCH_UP", 0)
    LIMIT_401K_TOTAL = _d["LIMIT_401K_TOTAL"]

    LIMIT_IRA = _d["LIMIT_IRA"]
    LIMIT_IRA_CATCH_UP = _d["LIMIT_IRA_CATCH_UP"]

    LIMIT_HSA_INDIVIDUAL = _d["LIMIT_HSA_INDIVIDUAL"]
    LIMIT_HSA_FAMILY = _d["LIMIT_HSA_FAMILY"]
    LIMIT_HSA_CATCH_UP = _d["LIMIT_HSA_CATCH_UP"]

    LIMIT_SEP_IRA = _d["LIMIT_SEP_IRA"]
    SEP_IRA_COMPENSATION_CAP = _d["SEP_IRA_COMPENSATION_CAP"]

    LIMIT_SIMPLE_IRA = _d["LIMIT_SIMPLE_IRA"]
    LIMIT_SIMPLE_IRA_CATCH_UP = _d["LIMIT_SIMPLE_IRA_CATCH_UP"]

    LIMIT_529_ANNUAL_GIFT_EXCLUSION = _d["LIMIT_529_ANNUAL_GIFT_EXCLUSION"]
    LIMIT_529_SUPERFUND = _d["LIMIT_529_SUPERFUND"]

    # ── Non-inflation-adjusted constants ──
    DEFAULT_RETIREMENT_AGE = 67
    DEFAULT_LIFE_EXPECTANCY = 95
    SPENDING_RATIO_HOUSEHOLD = 0.85  # 85% of pre-retirement income
    SPENDING_RATIO_SINGLE = 0.80  # 80% of pre-retirement income
    FALLBACK_SPENDING_HOUSEHOLD = 80_000  # If no income data available
    FALLBACK_SPENDING_SINGLE = 60_000
    # Default spending reduction for survivor scenario: household typically
    # spends 20% less after a spouse dies (1 - SPENDING_RATIO_SINGLE).
    SURVIVOR_SPENDING_REDUCTION = 0.20

    # Catch-up contribution eligibility ages (IRS rules — watch SECURE 3.0)
    CATCH_UP_AGE_401K = 50  # Age 50+: 401k / 403b / IRA catch-up eligible
    CATCH_UP_AGE_HSA = 55  # Age 55+: HSA catch-up eligible
    # SECURE 2.0 super catch-up for ages 60-63 (effective 2025+)
    CATCH_UP_AGE_SUPER_401K_START = 60
    CATCH_UP_AGE_SUPER_401K_END = 63

    @classmethod
    def for_year(cls, year: int) -> dict:
        """Return contribution limits for `year`; projects forward if year is not hardcoded."""
        return _resolve(_RETIREMENT_LIMITS, _RETIREMENT_PROJ, year)


# =========================================================================
# SOCIAL SECURITY
# =========================================================================


class SS:
    """Social Security parameters."""

    # Historical Social Security taxable maximum by year (SSA.gov)
    HISTORICAL_TAXABLE_MAX: Dict[int, int] = {
        1990: 51_300, 1991: 53_400, 1992: 55_500, 1993: 57_600,
        1994: 60_600, 1995: 61_200, 1996: 62_700, 1997: 65_400,
        1998: 68_400, 1999: 72_600, 2000: 76_200, 2001: 80_400,
        2002: 84_900, 2003: 87_000, 2004: 87_900, 2005: 90_000,
        2006: 94_200, 2007: 97_500, 2008: 102_000, 2009: 106_800,
        2010: 106_800, 2011: 106_800, 2012: 110_100, 2013: 113_700,
        2014: 117_000, 2015: 118_500, 2016: 118_500, 2017: 127_200,
        2018: 128_400, 2019: 132_900, 2020: 137_700, 2021: 142_800,
        2022: 147_000, 2023: 160_200, 2024: 168_600, 2025: 176_100,
        2026: 184_500,
    }

    # COLA rate for projecting taxable max beyond the table
    TAXABLE_MAX_COLA = 0.03

    # ── Inflation-adjusted — auto-selected for current tax year ──
    TAX_YEAR = datetime.date.today().year
    _d = _resolve(_SS_DATA, _SS_PROJ)

    TAXABLE_MAX = _d["TAXABLE_MAX"]

    # PIA bend points (monthly AIME amounts)
    BEND_POINT_1 = _d["BEND_POINT_1"]
    BEND_POINT_2 = _d["BEND_POINT_2"]

    # ── Non-inflation-adjusted constants ──

    # Replacement rates at each PIA segment
    RATE_1 = 0.90  # 90% of AIME up to 1st bend point
    RATE_2 = 0.32  # 32% between bend points
    RATE_3 = 0.15  # 15% above 2nd bend point

    # Wage growth assumption for AIME estimation
    WAGE_GROWTH = 0.025  # 2.5% per year

    # Annual benefit COLA — SSA announces each October; 2.5% confirmed for 2025 and 2026.
    # Distinct from WAGE_GROWTH (AIME estimation) and TAXABLE_MAX_COLA (wage base projection).
    # Source: ssa.gov/cost-of-living
    COLA = 0.025  # 2.5% — 2025/2026 confirmed rate

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

    @classmethod
    def taxable_max_for_year(cls, year: int) -> float:
        """Return the SS taxable maximum for a specific year.

        Uses historical table when available; projects forward from the
        latest known year at ~3% COLA for future years.
        """
        if year in cls.HISTORICAL_TAXABLE_MAX:
            return float(cls.HISTORICAL_TAXABLE_MAX[year])
        max_known = max(cls.HISTORICAL_TAXABLE_MAX)
        if year > max_known:
            base = cls.HISTORICAL_TAXABLE_MAX[max_known]
            return float(base) * (1 + cls.TAXABLE_MAX_COLA) ** (year - max_known)
        # year before table — use earliest known
        min_known = min(cls.HISTORICAL_TAXABLE_MAX)
        return float(cls.HISTORICAL_TAXABLE_MAX[min_known])

    @classmethod
    def for_year(cls, year: int) -> dict:
        """Return Social Security parameters for `year`; projects forward if not hardcoded."""
        return _resolve(_SS_DATA, _SS_PROJ, year)


# =========================================================================
# MEDICARE & IRMAA
# =========================================================================


class MEDICARE:
    """Medicare costs and IRMAA brackets."""

    # ── Inflation-adjusted — auto-selected for current tax year ──
    TAX_YEAR = datetime.date.today().year
    _d = _resolve(_MEDICARE_DATA, _MEDICARE_PROJ)

    PART_B_MONTHLY = _d["PART_B_MONTHLY"]
    PART_D_MONTHLY = _d["PART_D_MONTHLY"]
    IRMAA_BRACKETS_SINGLE: List[Tuple[float, float, float]] = _d["IRMAA_BRACKETS_SINGLE"]
    IRMAA_BRACKETS_MARRIED: List[Tuple[float, float, float]] = _d.get("IRMAA_BRACKETS_MARRIED", _d["IRMAA_BRACKETS_SINGLE"])

    # Medigap national average — year-keyed (Plan G approximate)
    _MEDIGAP_DATA: Dict[int, float] = {
        2024: 160.00,
        2025: 170.00,
        2026: 180.00,
    }

    @classmethod
    def medigap_for_year(cls, year: int | None = None) -> float:
        """Return Medigap monthly premium for the given year."""
        y = year if year is not None else datetime.date.today().year
        if y in cls._MEDIGAP_DATA:
            return cls._MEDIGAP_DATA[y]
        # Project at ~5% from the latest known anchor
        anchor = max(k for k in cls._MEDIGAP_DATA if k <= y) if any(k <= y for k in cls._MEDIGAP_DATA) else max(cls._MEDIGAP_DATA)
        base = cls._MEDIGAP_DATA[anchor]
        return round(base * (1.05) ** (y - anchor), 2)

    # Current-year value for backward compatibility
    MEDIGAP_MONTHLY = _MEDIGAP_DATA.get(datetime.date.today().year, 180.00)

    # ── Non-inflation-adjusted constants ──
    ELIGIBILITY_AGE = 65

    # IRMAA uses income from 2 years prior — start planning 2 years before eligibility
    IRMAA_PLANNING_AGE = 63

    @classmethod
    def for_year(cls, year: int) -> dict:
        """Return Medicare costs and IRMAA brackets for `year`; projects if not hardcoded."""
        return _resolve(_MEDICARE_DATA, _MEDICARE_PROJ, year)


# =========================================================================
# HEALTHCARE COSTS
# =========================================================================


class HEALTHCARE:
    """Healthcare cost assumptions with year-keyed base data and inflation projection."""

    # Year-keyed base values (update annually or when new data is available)
    # Sources: KFF Health Insurance Marketplace Calculator (ACA), Genworth Cost of Care Survey (LTC)
    _HEALTHCARE_DATA: Dict[int, Dict] = {
        2024: {
            "ACA_MONTHLY_SINGLE": 575,
            "ACA_MONTHLY_COUPLE": 1_150,
            "LTC_FACILITY_MONTHLY": 8_000,
            "LTC_HOME_CARE_MONTHLY": 1_900,  # Genworth median home health aide
            "OOP_ANNUAL": 2_800,             # KFF average out-of-pocket (dental/vision/copays)
        },
        2025: {
            "ACA_MONTHLY_SINGLE": 600,
            "ACA_MONTHLY_COUPLE": 1_200,
            "LTC_FACILITY_MONTHLY": 8_500,
            "LTC_HOME_CARE_MONTHLY": 1_966,
            "OOP_ANNUAL": 2_950,
        },
        2026: {
            "ACA_MONTHLY_SINGLE": 636,
            "ACA_MONTHLY_COUPLE": 1_272,
            "LTC_FACILITY_MONTHLY": 9_010,
            "LTC_HOME_CARE_MONTHLY": 2_083,   # ~6% medical inflation from 2025
            "OOP_ANNUAL": 3_127,
        },
    }

    # Medical inflation assumption
    DEFAULT_MEDICAL_INFLATION = 6.0  # Percent per year

    @classmethod
    def for_year(cls, year: int | None = None) -> dict:
        """Return healthcare cost data for `year`, projecting with medical inflation for future years."""
        y = year if year is not None else datetime.date.today().year
        anchor = _best_year(cls._HEALTHCARE_DATA, y)
        base = cls._HEALTHCARE_DATA[anchor]
        if y == anchor:
            return dict(base)
        factor = (1 + cls.DEFAULT_MEDICAL_INFLATION / 100) ** (y - anchor)
        return {k: int(round(v * factor)) for k, v in base.items()}

    # Current-year values for backward compatibility (computed from data table directly)
    _hc_year = datetime.date.today().year
    _hc_anchor = _best_year(_HEALTHCARE_DATA, _hc_year)
    _hc_base = _HEALTHCARE_DATA[_hc_anchor]
    if _hc_year == _hc_anchor:
        _hc_current = dict(_hc_base)
    else:
        _hc_factor = (1 + 6.0 / 100) ** (_hc_year - _hc_anchor)
        _hc_current = {k: int(round(v * _hc_factor)) for k, v in _hc_base.items()}
    ACA_MONTHLY_SINGLE = _hc_current["ACA_MONTHLY_SINGLE"]
    ACA_MONTHLY_COUPLE = _hc_current["ACA_MONTHLY_COUPLE"]

    # Out-of-pocket (dental, vision, copays) — now year-keyed
    OOP_ANNUAL = _hc_current["OOP_ANNUAL"]

    # Long-term care defaults (national medians, now year-keyed)
    LTC_FACILITY_MONTHLY = _hc_current["LTC_FACILITY_MONTHLY"]
    LTC_HOME_CARE_MONTHLY = _hc_current["LTC_HOME_CARE_MONTHLY"]
    LTC_DEFAULT_MONTHS_HOME = 12  # Average months home care first
    LTC_DEFAULT_MONTHS_FACILITY = 16  # Average months in facility

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

    # Age when RMDs begin (SECURE 2.0: 73 for born 1951-1959, 75 for born 1960+)
    TRIGGER_AGE = 73  # Default for born before 1960
    TRIGGER_AGE_2033 = 75  # For born 1960+, effective 2033
    TRIGGER_AGE_BIRTH_YEAR_THRESHOLD = 1960  # Birth year cutoff for age-75 rule

    @classmethod
    def trigger_age_for_birth_year(cls, birth_year: int | None) -> int:
        """Return RMD start age based on birth year (SECURE 2.0)."""
        if birth_year is not None and birth_year >= cls.TRIGGER_AGE_BIRTH_YEAR_THRESHOLD:
            return cls.TRIGGER_AGE_2033
        return cls.TRIGGER_AGE

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
    """College cost assumptions (CollegeBoard data, year-keyed and inflation-projected).

    Source: CollegeBoard "Trends in College Pricing" annual report.
    Update the _COLLEGE_COST_DATA table each fall when CollegeBoard publishes
    the new academic year data (typically October/November).
    """

    # Year-keyed annual base costs (academic year beginning in that calendar year)
    _COLLEGE_COST_DATA: Dict[int, Dict[str, int]] = {
        2024: {
            "public_in_state": 23_250,
            "public_out_of_state": 41_000,
            "private": 57_000,
        },
        2025: {
            "public_in_state": 24_030,
            "public_out_of_state": 42_400,
            "private": 59_000,
        },
        2026: {
            "public_in_state": 24_960,   # ~3.9% increase per CollegeBoard trend
            "public_out_of_state": 44_000,
            "private": 61_200,
        },
    }
    COLLEGE_COSTS_BASE_YEAR: int = max(_COLLEGE_COST_DATA.keys())  # auto-updates when new data added

    COLLEGE_INFLATION_RATE = 0.05  # 5% annual college cost inflation (long-run average)
    DEFAULT_ANNUAL_RETURN = 0.06  # 6% expected return for 529 plan
    COLLEGE_YEARS = 4

    # Current-year costs (used as default where a single value is needed)
    COLLEGE_COSTS: Dict[str, int] = _COLLEGE_COST_DATA[COLLEGE_COSTS_BASE_YEAR]

    @classmethod
    def costs_for_year(cls, year: int) -> dict:
        """Return college costs for `year`, using year-keyed data when available
        and projecting forward with COLLEGE_INFLATION_RATE from the newest data point."""
        anchor = _best_year(cls._COLLEGE_COST_DATA, year)
        base = cls._COLLEGE_COST_DATA[anchor]
        if year == anchor:
            return dict(base)
        factor = (1 + cls.COLLEGE_INFLATION_RATE) ** (year - anchor)
        return {k: int(round(v * factor)) for k, v in base.items()}


# =========================================================================
# FIRE / WITHDRAWAL / SIMULATION DEFAULTS
# =========================================================================


class FIRE:
    """FIRE metrics and simulation assumptions."""

    # Safe withdrawal rate
    DEFAULT_WITHDRAWAL_RATE = 0.04  # 4% rule
    FI_MULTIPLIER = 25  # 1 / 0.04

    # Default annual spending used for retirement target (25× rule) when no
    # income data is available.  Matches RETIREMENT.FALLBACK_SPENDING_HOUSEHOLD.
    DEFAULT_ANNUAL_SPENDING = 80_000

    # Default annual contribution used in net-worth forecasting when the caller
    # does not supply an override (401k + IRA rough combined max, round number).
    DEFAULT_ANNUAL_CONTRIBUTION = 24_000

    # Return / inflation assumptions
    DEFAULT_EXPECTED_RETURN = 0.07  # 7% nominal
    DEFAULT_EXPECTED_RETURN_PCT = Decimal("7.00")  # Same as above, in percent form
    DEFAULT_POST_RETIREMENT_RETURN = 0.05  # 5% nominal (conservative)
    DEFAULT_POST_RETIREMENT_RETURN_PCT = Decimal("5.00")
    DEFAULT_INFLATION = 0.03  # 3% general inflation
    DEFAULT_INFLATION_PCT = Decimal("3.00")
    DEFAULT_REAL_RETURN = DEFAULT_EXPECTED_RETURN - DEFAULT_INFLATION  # 4%
    DEFAULT_WITHDRAWAL_RATE_PCT = Decimal("4.00")  # Same as DEFAULT_WITHDRAWAL_RATE
    DEFAULT_CAPITAL_GAINS_RATE = Decimal("0.15")  # 15% — middle LTCG bracket
    DEFAULT_CAPITAL_GAINS_RATE_PCT = Decimal("15.00")

    # Monte Carlo defaults
    MC_PRE_RETIREMENT_RETURN = 7.0  # Percent
    MC_POST_RETIREMENT_RETURN = 5.0
    MC_VOLATILITY = 15.0
    MC_INFLATION = 3.0
    MC_DEFAULT_SIMS = 2_500
    MC_QUICK_SIMS = 500

    # ── Monte Carlo asset class return/volatility assumptions ──────────────
    # Source: Vanguard Capital Markets Model long-run estimates (annualized)
    # Update periodically as long-run equilibrium estimates evolve.
    MC_ASSET_CLASS_DEFAULTS: Dict[str, Dict[str, float]] = {
        "stocks":      {"mean": 0.10, "std": 0.18},  # US equity: ~10% / 18% vol
        "bonds":       {"mean": 0.04, "std": 0.06},  # Core fixed income
        "real_estate": {"mean": 0.07, "std": 0.12},  # REIT/direct
        "cash":        {"mean": 0.03, "std": 0.01},  # Money market / T-bills
    }

    # ── Monte Carlo correlation matrix (stocks, bonds, real_estate, cash) ──
    # Based on historical 30-year correlations (1994–2024)
    MC_CORRELATION_MATRIX: List[List[float]] = [
        [1.00, -0.10,  0.40,  0.00],
        [-0.10, 1.00,  0.20,  0.05],
        [ 0.40, 0.20,  1.00,  0.00],
        [ 0.00, 0.05,  0.00,  1.00],
    ]

    # ── On-track threshold (used in financial plan summary and smart insights) ──
    # A simulation success rate >= this value is considered "on track".
    # 70% means the portfolio survives through retirement in 7 out of 10 scenarios.
    MC_ON_TRACK_SUCCESS_RATE = 70.0  # Percent

    # Tax rate caps for withdrawal strategy (prevent unreasonable gross-up)
    MAX_CAPITAL_GAINS_RATE = 0.50
    MAX_INCOME_TAX_RATE = 0.70

    # COLA rates used in multi-year projection services
    # Federal income tax brackets are adjusted annually for CPI per IRS Rev. Proc.
    DEFAULT_BRACKET_COLA = 0.025  # ~2.5% — approximates recent IRS bracket adjustments
    # IRMAA thresholds are indexed to CPI-U; historically closer to 3%.
    IRMAA_COLA = 0.03  # 3% CPI-linked IRMAA threshold projection rate

    # Conservative pre-retirement growth rate for RMD/tax-bucket projections.
    # Lower than DEFAULT_EXPECTED_RETURN (7%) to account for a more bond-heavy
    # near-retirement allocation.
    DEFAULT_GROWTH_RATE = 0.06  # 6% nominal pre-retirement


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

    # ── Financial Plan Summary thresholds (used in financial_plan.py) ──────
    # Retirement gap above this in $/month triggers "critical" status
    RETIREMENT_GAP_CRITICAL = 2_000
    # High-interest debt above this triggers "critical" status
    DEBT_HIGH_INTEREST_CRITICAL = 20_000
    DEBT_HIGH_INTEREST_MODERATE = 5_000
    # Net worth above this triggers umbrella insurance recommendation
    UMBRELLA_RECOMMEND_NET_WORTH = 500_000
    # Life insurance need = LIFE_INSURANCE_INCOME_MULTIPLE × gross annual income
    # Falls back to LIFE_INSURANCE_FALLBACK_NEED when income cannot be determined
    LIFE_INSURANCE_INCOME_MULTIPLE = 10
    LIFE_INSURANCE_FALLBACK_NEED = 500_000  # Conservative fallback (not $1M)
    # Insurance coverage score thresholds
    INSURANCE_SCORE_GOOD = 80
    INSURANCE_SCORE_CRITICAL = 40
    # Emergency fund target (months of expenses)
    EMERGENCY_FUND_TARGET_MONTHS = EMERGENCY_FUND_EXCELLENT  # 6 months
    EMERGENCY_FUND_CRITICAL_MONTHS = 1


# =========================================================================
# SMART INSIGHTS THRESHOLDS
# =========================================================================


class SMART_INSIGHTS:
    """Thresholds used by SmartInsightsService to decide when to fire insights."""

    # Expense-ratio above which a fund-fee insight fires (0.30 %)
    FEE_DRAG_THRESHOLD = 0.003
    # Single-position concentration above which an insight fires (10 %)
    CONCENTRATION_THRESHOLD = 0.10
    # Minimum portfolio value required before concentration insight fires ($)
    CONCENTRATION_MIN_VALUE = 10_000

    # Settlement balance: amounts within this band are treated as "even"
    # (avoids noise from floating-point rounding on small household splits)
    SETTLEMENT_EVEN_BAND = 0.005  # $0.005 — half a cent


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

    # Major life events
    WEDDING_COST = Decimal("30000")
    DIVORCE_COST = Decimal("15000")
    NEWBORN_FIRST_YEAR = Decimal("20000")  # First-year costs (nursery, supplies, etc.)


# =========================================================================
# DEBT PAYOFF DEFAULTS
# =========================================================================


class DEBT:
    """Default assumptions for debt payoff calculations."""

    # Credit card minimum payment
    MIN_PAYMENT_RATE = Decimal("0.02")  # 2% of balance
    MIN_PAYMENT_FLOOR = Decimal("25.00")  # $25 minimum floor

    # Fallback interest rate when the account has no rate set
    DEFAULT_INTEREST_RATE = Decimal("18.0")  # 18% — typical credit card APR

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
    DEFAULT_MONTHLY_EXPENSES = Decimal("3000")  # Monthly (median US household)

    # Vacation fund template target
    VACATION_TARGET = Decimal("4000")  # ANNUAL

    # Home down payment template (20% of ~$300K median US home price)
    HOME_DOWN_PAYMENT = Decimal("60000")  # ANNUAL

    # Debt payoff reserve: fraction of total debt to set aside
    DEBT_PAYOFF_RESERVE_RATE = Decimal("0.10")  # 10% of total debt
    DEBT_PAYOFF_RESERVE_MIN = Decimal("1000")  # Minimum reserve regardless of debt size


# =========================================================================
# NET WORTH BENCHMARKS  ← UPDATE EVERY 3 YEARS (Federal Reserve SCF)
# =========================================================================
#
# Source:  Federal Reserve Survey of Consumer Finances (SCF)
#          https://www.federalreserve.gov/econres/scfindex.htm
#
# How to update
# -------------
# The Fed publishes new SCF data every 3 years (2022, 2025, 2028 …).
# When new data is released:
#
#   1. Run the scraper first — it will attempt to pull the latest tables:
#          python -m app.services.scf_benchmark_service --scrape
#      If scraping succeeds, a JSON cache is written to
#          backend/app/constants/scf_cache.json
#      and the SCRAPED_AT / SURVEY_YEAR fields below are auto-updated.
#
#   2. If the scraper cannot reach the Fed website, update this file
#      manually:
#        a. Download the SCF summary tables from the URL above.
#        b. Find Table 2: "Family Net Worth, by Selected Characteristics".
#        c. Update SURVEY_YEAR, SCRAPED_AT, and the MEDIAN / MEAN dicts
#           for each age bracket.
#        d. Update FIDELITY_MILESTONES if new guidance has been published
#           (https://www.fidelity.com/viewpoints/retirement/how-much-money-should-I-have-saved).
#
# Data format
# -----------
# MEDIAN / MEAN:  Dict[age_bucket_label, net_worth_in_2022_dollars]
# Age buckets match the SCF publication: "under 35", "35-44", "45-54",
# "55-64", "65-74", "75+".
#
# FIDELITY_MILESTONES: Dict[age, multiple_of_salary]
# These are Fidelity's published "salary multiple" targets, used as a
# secondary "rule of thumb" benchmark.
# =========================================================================


class NET_WORTH_BENCHMARKS:
    """
    Age-adjusted net worth benchmarks for the 'Am I on track?' insight.

    DATA SOURCE: Federal Reserve Survey of Consumer Finances (SCF), 2022 and 2025
    SURVEY_YEAR: The year the underlying survey data was collected.
    SCRAPED_AT:  ISO-8601 timestamp of the last successful automated
                 scrape, or None if only static data has ever been used.

    NOTE: The 2025 SCF (collecting 2023 financial data) was released in late 2024.
    Values below reflect the 2022 survey (most recent fully published table).
    When the 2025 full data tables are released, run:
        python -m app.services.scf_benchmark_service --scrape
    and update SURVEY_YEAR to 2025.

    *** See the header comment above for update instructions. ***
    """

    SURVEY_YEAR: int = 2022
    SCRAPED_AT: str | None = None  # Set by scf_benchmark_service when scraped

    # ── SCF median net worth by age bracket (2022 dollars) ─────────────────
    # Source: SCF 2022 Table 2 – Median value of family net worth
    # https://www.federalreserve.gov/econres/scfindex.htm
    # NOTE: These are 2022 survey dollars. The 2025 release (2023 data) shows
    # roughly 8–12% increases across most brackets due to real estate appreciation
    # and equity market gains between 2019 and 2022. Update when 2025 tables publish.
    MEDIAN: Dict[str, float] = {
        "under 35":  39_000,
        "35-44":    135_600,
        "45-54":    247_200,
        "55-64":    364_270,
        "65-74":    409_900,
        "75+":      335_600,
    }

    # ── SCF mean net worth by age bracket (2022 dollars) ───────────────────
    MEAN: Dict[str, float] = {
        "under 35":  183_500,
        "35-44":    549_600,
        "45-54":  1_166_100,
        "55-64":  1_787_600,
        "65-74":  1_794_600,
        "75+":    1_624_100,
    }

    # ── Fidelity salary-multiple milestones ────────────────────────────────
    # Source: Fidelity "How much money should I have saved by age?"
    # https://www.fidelity.com/viewpoints/retirement/how-much-money-should-I-have-saved
    # Format: {age: target_multiple_of_gross_annual_salary}
    FIDELITY_MILESTONES: Dict[int, float] = {
        30: 1.0,
        35: 2.0,
        40: 3.0,
        45: 4.0,
        50: 6.0,
        55: 7.0,
        60: 8.0,
        67: 10.0,
    }

    # ── Scrape config ───────────────────────────────────────────────────────
    # URL of the Fed SCF landing page (scraped for data-table links)
    SCF_URL: str = "https://www.federalreserve.gov/econres/scfindex.htm"
    # How many years before the static data is considered stale for UI warning
    STALE_AFTER_YEARS: int = 3
    DEBT_PAYOFF_RESERVE_MIN = Decimal("1000")  # Minimum reserve regardless of debt size


# =========================================================================
# EQUITY COMPENSATION
# =========================================================================


# ── AMT year-keyed data ──────────────────────────────────────────────────
_AMT_DATA: dict[int, dict] = {
    2024: {
        "AMT_EXEMPTION_SINGLE": 85_700,
        "AMT_EXEMPTION_MARRIED": 133_300,
        "AMT_PHASEOUT_SINGLE": 609_350,
        "AMT_PHASEOUT_MARRIED": 1_218_700,
        "AMT_RATE_26_THRESHOLD": 232_600,
    },
    2025: {
        "AMT_EXEMPTION_SINGLE": 88_100,
        "AMT_EXEMPTION_MARRIED": 137_000,
        "AMT_PHASEOUT_SINGLE": 626_350,
        "AMT_PHASEOUT_MARRIED": 1_252_700,
        "AMT_RATE_26_THRESHOLD": 239_100,
    },
    2026: {
        # Projected ~3% COLA from 2025
        "AMT_EXEMPTION_SINGLE": 90_700,
        "AMT_EXEMPTION_MARRIED": 141_100,
        "AMT_PHASEOUT_SINGLE": 645_100,
        "AMT_PHASEOUT_MARRIED": 1_290_300,
        "AMT_RATE_26_THRESHOLD": 246_300,
    },
}
_AMT_PROJ: dict[str, tuple] = {
    "AMT_EXEMPTION_SINGLE": (0.03, 100),
    "AMT_EXEMPTION_MARRIED": (0.03, 100),
    "AMT_PHASEOUT_SINGLE": (0.03, 50),
    "AMT_PHASEOUT_MARRIED": (0.03, 100),
    "AMT_RATE_26_THRESHOLD": (0.03, 100),
}

# ── QBI year-keyed data ──────────────────────────────────────────────────
_QBI_DATA: dict[int, dict] = {
    2024: {
        "QBI_THRESHOLD_SINGLE": 191_950,
        "QBI_THRESHOLD_MARRIED": 383_900,
    },
    2025: {
        "QBI_THRESHOLD_SINGLE": 197_300,
        "QBI_THRESHOLD_MARRIED": 394_600,
    },
    2026: {
        # Projected ~5% COLA from 2025
        "QBI_THRESHOLD_SINGLE": 207_250,
        "QBI_THRESHOLD_MARRIED": 414_500,
    },
}
_QBI_PROJ: dict[str, tuple] = {
    "QBI_THRESHOLD_SINGLE": (0.05, 50),
    "QBI_THRESHOLD_MARRIED": (0.05, 100),
}

# ── WEP year-keyed data ──────────────────────────────────────────────────
_WEP_DATA: dict[int, dict] = {
    2024: {"WEP_MAX_MONTHLY_REDUCTION": 578},
    2025: {"WEP_MAX_MONTHLY_REDUCTION": 587},
    2026: {"WEP_MAX_MONTHLY_REDUCTION": 619},  # Projected ~COLA from 2025
}
_WEP_PROJ: dict[str, tuple] = {
    "WEP_MAX_MONTHLY_REDUCTION": (0.03, 1),
}

# ── QCD year-keyed data (SECURE 2.0: inflation-indexed from 2024) ────────
_QCD_DATA: dict[int, dict] = {
    2024: {"QCD_MAX_ANNUAL": 105_000},
    2025: {"QCD_MAX_ANNUAL": 108_000},
    2026: {"QCD_MAX_ANNUAL": 108_000},  # Unchanged or slightly higher; conservative
}
_QCD_PROJ: dict[str, tuple] = {
    "QCD_MAX_ANNUAL": (0.025, 1_000),  # SECURE 2.0 inflation-indexed
}


class AMT:
    """Alternative Minimum Tax year-keyed constants."""
    TAX_YEAR = datetime.date.today().year
    _d = _resolve(_AMT_DATA, _AMT_PROJ)
    AMT_EXEMPTION_SINGLE = _d["AMT_EXEMPTION_SINGLE"]
    AMT_EXEMPTION_MARRIED = _d["AMT_EXEMPTION_MARRIED"]
    AMT_PHASEOUT_SINGLE = _d["AMT_PHASEOUT_SINGLE"]
    AMT_PHASEOUT_MARRIED = _d["AMT_PHASEOUT_MARRIED"]
    AMT_RATE_26_THRESHOLD = _d["AMT_RATE_26_THRESHOLD"]
    AMT_RATE_26 = Decimal("0.26")
    AMT_RATE_28 = Decimal("0.28")

    @classmethod
    def for_year(cls, year: int) -> dict:
        return _resolve(_AMT_DATA, _AMT_PROJ, year)


class QBI:
    """Qualified Business Income deduction year-keyed constants."""
    TAX_YEAR = datetime.date.today().year
    _d = _resolve(_QBI_DATA, _QBI_PROJ)
    QBI_THRESHOLD_SINGLE = _d["QBI_THRESHOLD_SINGLE"]
    QBI_THRESHOLD_MARRIED = _d["QBI_THRESHOLD_MARRIED"]
    DEDUCTION_RATE = Decimal("0.20")

    @classmethod
    def for_year(cls, year: int) -> dict:
        return _resolve(_QBI_DATA, _QBI_PROJ, year)


class WEP:
    """Windfall Elimination Provision year-keyed constants."""
    TAX_YEAR = datetime.date.today().year
    _d = _resolve(_WEP_DATA, _WEP_PROJ)
    WEP_MAX_MONTHLY_REDUCTION = Decimal(str(_d["WEP_MAX_MONTHLY_REDUCTION"]))

    @classmethod
    def for_year(cls, year: int) -> dict:
        return _resolve(_WEP_DATA, _WEP_PROJ, year)


class QCD:
    """Qualified Charitable Distribution year-keyed constants (SECURE 2.0)."""
    TAX_YEAR = datetime.date.today().year
    _d = _resolve(_QCD_DATA, _QCD_PROJ)
    QCD_MAX_ANNUAL = _d["QCD_MAX_ANNUAL"]
    QCD_ELIGIBLE_AGE = Decimal("70.5")

    @classmethod
    def for_year(cls, year: int) -> dict:
        return _resolve(_QCD_DATA, _QCD_PROJ, year)


class EQUITY:
    """Stock options and equity compensation constants."""

    # AMT values now sourced from year-keyed AMT class
    AMT_EXEMPTION_SINGLE = AMT.AMT_EXEMPTION_SINGLE
    AMT_EXEMPTION_MARRIED = AMT.AMT_EXEMPTION_MARRIED
    AMT_PHASEOUT_SINGLE = AMT.AMT_PHASEOUT_SINGLE
    AMT_PHASEOUT_MARRIED = AMT.AMT_PHASEOUT_MARRIED
    AMT_RATE_26_THRESHOLD = AMT.AMT_RATE_26_THRESHOLD
    AMT_RATE_26 = Decimal("0.26")
    AMT_RATE_28 = Decimal("0.28")
    ISO_DISQUALIFYING_DISPOSITION_DAYS = 730
    NSO_TAX_TREATMENT = "ordinary_income"
    RSU_TAX_EVENT = "ordinary_income"
    # 100% exclusion applies to stock acquired after Sep 27, 2010 (IRC §1202(a)(4))
    QSBS_EXCLUSION_RATE = Decimal("1.00")


# =========================================================================
# ESPP (Section 423 Employee Stock Purchase Plan)
# =========================================================================


class ESPP:
    """Employee Stock Purchase Plan constants (IRC Section 423)."""

    MAX_DISCOUNT_RATE = Decimal("0.15")  # Max 15% discount under Section 423
    ANNUAL_PURCHASE_LIMIT = 25_000  # IRS Section 423 annual limit ($25K FMV)
    QUALIFYING_HOLDING_PERIOD_DAYS = 730  # 2 years from offering date
    QUALIFYING_PURCHASE_PERIOD_DAYS = 365  # 1 year from purchase date


# =========================================================================
# HEALTH SAVINGS ACCOUNT
# =========================================================================


class HSA:
    """Health Savings Account optimization constants."""

    INVESTMENT_THRESHOLD = Decimal("2000")
    DEFAULT_MEDICAL_EXPENSE_GROWTH = Decimal("0.06")
    MEDICARE_CUTOFF_AGE = 65
    NON_QUALIFIED_PENALTY_RATE = Decimal("0.20")
    INVESTMENT_RETURN_DEFAULT = Decimal("0.06")

    # HDHP limits — year-keyed (IRS Rev. Proc.)
    _HSA_HDHP_DATA: Dict[int, Dict] = {
        2024: {"MIN_DEDUCTIBLE_INDIVIDUAL": 1_600, "MIN_DEDUCTIBLE_FAMILY": 3_200, "MAX_OOP_INDIVIDUAL": 8_050, "MAX_OOP_FAMILY": 16_100},
        2025: {"MIN_DEDUCTIBLE_INDIVIDUAL": 1_650, "MIN_DEDUCTIBLE_FAMILY": 3_300, "MAX_OOP_INDIVIDUAL": 8_300, "MAX_OOP_FAMILY": 16_600},
        2026: {"MIN_DEDUCTIBLE_INDIVIDUAL": 1_700, "MIN_DEDUCTIBLE_FAMILY": 3_400, "MAX_OOP_INDIVIDUAL": 8_500, "MAX_OOP_FAMILY": 17_000},
    }

    @classmethod
    def hdhp_for_year(cls, year: int | None = None) -> dict:
        """Return HDHP limits for the given year, projecting ~3% for unknown years."""
        y = year if year is not None else datetime.date.today().year
        anchor = _best_year(cls._HSA_HDHP_DATA, y)
        base = cls._HSA_HDHP_DATA[anchor]
        if y == anchor:
            return dict(base)
        # Project forward at ~3% CPI, round to nearest $50
        factor = (1.03) ** (y - anchor)
        return {k: int(round(v * factor / 50) * 50) for k, v in base.items()}

    # Current-year values for backward compatibility
    _hdhp_current = _HSA_HDHP_DATA.get(datetime.date.today().year, _HSA_HDHP_DATA[max(_HSA_HDHP_DATA)])
    HDHP_MIN_DEDUCTIBLE_INDIVIDUAL = _hdhp_current["MIN_DEDUCTIBLE_INDIVIDUAL"]
    HDHP_MIN_DEDUCTIBLE_FAMILY = _hdhp_current["MIN_DEDUCTIBLE_FAMILY"]
    HDHP_MAX_OOP_INDIVIDUAL = _hdhp_current["MAX_OOP_INDIVIDUAL"]
    HDHP_MAX_OOP_FAMILY = _hdhp_current["MAX_OOP_FAMILY"]


# =========================================================================
# TREASURY SECURITIES
# =========================================================================


class TREASURY:
    """I-Bond, T-Bill, T-Note, and TIPS constants."""

    I_BOND_ANNUAL_LIMIT_ELECTRONIC = 10_000
    I_BOND_ANNUAL_LIMIT_PAPER_TAX_REFUND = 5_000
    I_BOND_MIN_HOLD_MONTHS = 12
    I_BOND_EARLY_REDEMPTION_PENALTY_MONTHS = 3
    I_BOND_MAX_TERM_YEARS = 30
    TIPS_DEFLATION_FLOOR = Decimal("1.0")
    TBILL_MATURITIES_WEEKS = [4, 8, 13, 17, 26, 52]
    TNOTE_MATURITIES_YEARS = [2, 3, 5, 7, 10]
    TBOND_MATURITIES_YEARS = [20, 30]


# =========================================================================
# ESTATE PLANNING
# =========================================================================


_ESTATE_DATA: dict[int, dict] = {
    2024: {"FEDERAL_EXEMPTION": 13_610_000, "ANNUAL_GIFT_EXCLUSION": 18_000},
    2025: {"FEDERAL_EXEMPTION": 13_990_000, "ANNUAL_GIFT_EXCLUSION": 19_000},
    2026: {"FEDERAL_EXEMPTION": 13_990_000, "ANNUAL_GIFT_EXCLUSION": 19_000},  # projected same, COLA TBD
}
_ESTATE_PROJ: dict[str, tuple] = {
    "FEDERAL_EXEMPTION": (0.03, 10_000),
    "ANNUAL_GIFT_EXCLUSION": (0.025, 1_000),
}


class ESTATE:
    """Estate and beneficiary planning constants with year-keyed data."""

    # Current-year values for backward compatibility
    _d = _resolve(_ESTATE_DATA, _ESTATE_PROJ)
    FEDERAL_EXEMPTION = _d["FEDERAL_EXEMPTION"]
    ANNUAL_GIFT_EXCLUSION = _d["ANNUAL_GIFT_EXCLUSION"]
    ANNUAL_GIFT_EXCLUSION_MARRIED = _d["ANNUAL_GIFT_EXCLUSION"] * 2

    FEDERAL_TAX_RATE = Decimal("0.40")
    PORTABILITY_ELECTION_DEADLINE_MONTHS = 9
    # TCJA exemption extended through 2034 by One Big Beautiful Bill Act (signed 2025).
    # Sunset risk deferred to 2034, not imminent.
    TCJA_SUNSET_RISK = False
    TCJA_SUNSET_YEAR = 2034

    @classmethod
    def for_year(cls, year: int) -> dict:
        """Return estate constants for a specific year (projects forward if not hardcoded)."""
        data = _resolve(_ESTATE_DATA, _ESTATE_PROJ, year)
        data["ANNUAL_GIFT_EXCLUSION_MARRIED"] = data["ANNUAL_GIFT_EXCLUSION"] * 2
        data["FEDERAL_TAX_RATE"] = float(cls.FEDERAL_TAX_RATE)
        return data


# =========================================================================
# STRESS TESTING
# =========================================================================


class STRESS_TEST:
    """Historical market stress scenario parameters (hardcoded)."""

    SCENARIOS: dict = {
        "market_crash_30": {
            "label": "30% Market Drop",
            "equity_drop": Decimal("-0.30"),
            "bond_change": Decimal("0.05"),
            "duration_years": 1.0,
        },
        "dot_com_2000": {
            "label": "Dot-Com Bust (2000–2002)",
            "equity_drop": Decimal("-0.49"),
            "bond_change": Decimal("0.12"),
            "duration_years": 2.5,
        },
        "gfc_2008": {
            "label": "Financial Crisis (2008–2009)",
            "equity_drop": Decimal("-0.57"),
            "bond_change": Decimal("0.08"),
            "duration_years": 1.5,
        },
        "covid_2020": {
            "label": "COVID Crash (Feb–Mar 2020)",
            "equity_drop": Decimal("-0.34"),
            "bond_change": Decimal("0.08"),
            "duration_years": 0.15,
        },
        "stagflation_1970s": {
            "label": "1970s Stagflation",
            "equity_drop": Decimal("-0.45"),
            "inflation_spike": Decimal("0.14"),
            "bond_change": Decimal("-0.10"),
            "duration_years": 10.0,
        },
        "rate_shock_200bps": {
            "label": "+200bps Rate Shock",
            "equity_drop": Decimal("-0.10"),
            "bond_change": None,  # Calculated dynamically from duration
            "rate_increase_bps": 200,
            "duration_years": 0.5,
        },
    }
    BOND_PRICE_SENSITIVITY_PER_YEAR_PER_100BPS = Decimal("-0.01")


# =========================================================================
# CASH FLOW TIMING
# =========================================================================


class CASH_FLOW_TIMING:
    """Paycheck and bill timing constants."""

    PAYCHECK_FREQUENCIES = {
        "weekly": 52,
        "biweekly": 26,
        "semimonthly": 24,
        "monthly": 12,
    }
    DEFAULT_FREQUENCY = "biweekly"
    LOW_BALANCE_WARNING_USD = Decimal("500")
    BILL_WARNING_DAYS_BEFORE_SHORTFALL = 3


# =========================================================================
# PENSION MODELING
# =========================================================================


class PENSION:
    """Defined benefit pension modeling constants (2026)."""

    COLA_DEFAULT_RATE = Decimal("0.02")
    SURVIVOR_100_COST_PCT = Decimal("0.10")
    SURVIVOR_50_COST_PCT = Decimal("0.05")
    WEP_MAX_MONTHLY_REDUCTION = WEP.WEP_MAX_MONTHLY_REDUCTION
    GPO_REDUCTION_RATE = Decimal("0.667")
    LUMP_SUM_HURDLE_RATE = Decimal("0.045")
    WEP_SUBSTANTIAL_EARNINGS_YEARS_FULL_EXEMPTION = 30
    WEP_SUBSTANTIAL_EARNINGS_MINIMUM_WAGE_MULTIPLE = 2  # 2x minimum wage threshold
    PENSION_FULLY_TAXABLE_DEFAULT = True


# =========================================================================
# VARIABLE INCOME
# =========================================================================


class VARIABLE_INCOME:
    """Variable and self-employment income planning constants.

    Tax rates (2026 IRS):
      SE_TAX_RATE              — statutory 15.3% (12.4% SS + 2.9% Medicare)
      SE_TAX_DEDUCTIBLE_HALF   — you deduct 50% of SE tax before income tax,
                                  so the *effective* rate is:
                                  SE_TAX_RATE * (1 - SE_TAX_DEDUCTIBLE_HALF * SE_TAX_RATE)
                                  ≈ 14.13%  (use SE_TAX_RATE_EFFECTIVE below)
      SE_TAX_RATE_EFFECTIVE    — pre-computed effective rate for UI defaults

    Federal bracket defaults (FED_TAX_RATE_DEFAULT) are set to 22%, the most
    common bracket for self-employed individuals in the $44k–$100k net income
    range.  Users should override in the planner settings for their bracket.

    SAFE_FLOOR_PCT             — recommended monthly spending cap as a fraction
                                  of the lowest monthly income in the trailing
                                  12 months (80% leaves a 20% tax/savings buffer).
    """

    SMOOTHING_MONTHS = 12
    EMERGENCY_FUND_MONTHS_MINIMUM = 9
    QUARTERLY_TAX_DUE_MONTHS = [4, 6, 9, 1]
    SE_TAX_RATE = Decimal("0.153")
    SE_TAX_DEDUCTIBLE_HALF = Decimal("0.50")
    # Effective SE rate after the 50% above-the-line deduction:
    # 0.153 × (1 − 0.50 × 0.153) ≈ 0.1413
    SE_TAX_RATE_EFFECTIVE = Decimal("0.1413")
    FED_TAX_RATE_DEFAULT = Decimal("0.22")   # 22% bracket default
    STATE_TAX_RATE_DEFAULT = Decimal("0.00") # 0% — user must set for their state
    SAFE_FLOOR_PCT = Decimal("0.80")         # 80% of worst month = spending cap
    QBI_DEDUCTION_RATE = Decimal("0.20")
    QBI_THRESHOLD_SINGLE: Decimal = Decimal(str(QBI.QBI_THRESHOLD_SINGLE))
    QBI_THRESHOLD_MARRIED: Decimal = Decimal(str(QBI.QBI_THRESHOLD_MARRIED))
    SAFE_HARBOR_110_PCT_INCOME_THRESHOLD = 150_000
    SAFE_HARBOR_RATE_NORMAL = Decimal("1.00")
    SAFE_HARBOR_RATE_HIGH_INCOME = Decimal("1.10")
    # IRS safe-harbour: pay at least 90% of current-year tax to avoid penalty.
    # (The 100%/110%-of-prior-year alternative is covered by the rates above.)
    SAFE_HARBOR_CURRENT_YEAR_RATE = Decimal("0.90")


# =========================================================================
# LENDING
# =========================================================================


class LENDING:
    """Loan origination and affordability constants."""

    MAX_DTI_CONVENTIONAL = Decimal("0.43")
    MAX_DTI_FHA = Decimal("0.50")
    MAX_DTI_VA = Decimal("0.41")
    FRONT_END_DTI_LIMIT = Decimal("0.28")
    PRIME_CREDIT_SCORE_THRESHOLD = 720
    POINTS_BREAKEVEN_MONTHS = 60
    AUTO_DEPRECIATION_NEW_ANNUAL = Decimal("0.15")
    AUTO_DEPRECIATION_USED_ANNUAL = Decimal("0.10")
    LEASE_MONEY_FACTOR_TO_APR = 2400
    STUDENT_LOAN_IDR_CAP_PCT = Decimal("0.10")


# =========================================================================
# CHARITABLE GIVING
# =========================================================================


class CHARITABLE:
    """Charitable giving optimization constants (2026)."""

    QCD_MAX_ANNUAL = QCD.QCD_MAX_ANNUAL
    QCD_ELIGIBLE_AGE = QCD.QCD_ELIGIBLE_AGE
    BUNCHING_HORIZON_YEARS = 3
    DEDUCTION_LIMIT_CASH_PCT_AGI = Decimal("0.60")
    DEDUCTION_LIMIT_PROPERTY_PCT_AGI = Decimal("0.30")
    DEDUCTION_LIMIT_APPRECIATED_PCT_AGI = Decimal("0.30")
    CARRYFORWARD_YEARS = 5
    APPRECIATED_SECURITY_AVOIDS_LTCG = True


# =========================================================================
# JOINT SOCIAL SECURITY
# =========================================================================


class JOINT_SS:
    """Joint Social Security optimization constants."""

    SPOUSAL_BENEFIT_PCT = Decimal("0.50")
    SURVIVOR_BENEFIT_PCT = Decimal("1.00")
    SURVIVOR_BENEFIT_MIN_AGE = 60
    DIVORCED_SPOUSE_MIN_MARRIAGE_YEARS = 10
    DUAL_ENTITLEMENT_RULE = True
    GPO_REDUCTION_RATE = Decimal("0.667")
    WEP_SUBSTANTIAL_EARNINGS_FULL_EXEMPTION_YEARS = 30
    RESTRICTED_APPLICATION_BIRTH_YEAR_CUTOFF = 1954


# =========================================================================
# TAX BUCKET ANALYSIS
# =========================================================================


class TAX_BUCKETS:
    """Tax bucket analysis and RMD tax bomb constants."""

    PRE_TAX_WARNING_THRESHOLD_PCT = Decimal("0.85")
    # Default pre-retirement growth rate for tax-bucket projections (Decimal form).
    # Use FIRE.DEFAULT_GROWTH_RATE (float) for non-Decimal math.
    DEFAULT_GROWTH_RATE = Decimal("0.06")  # 6% nominal
    RMD_BOMB_MULTIPLE_OF_SPENDING = Decimal("2.0")
    OPTIMAL_CONVERSION_BRACKET = Decimal("0.22")
    PROJECTION_DEFAULT_YEARS = 10
    INCOME_GROWTH_DEFAULT = Decimal("0.025")
    ROTH_LADDER_SEASONING_YEARS = 5


# =========================================================================
# BOND LADDER — FALLBACK TREASURY RATES
# =========================================================================


class CRYPTO_TAX:
    """Crypto tax classification constants.

    As of 2026, crypto is classified as property (like collectibles) under IRC §1221.
    This means:
    - No wash-sale rule (IRC §1091 does not apply to property)
    - Short-term gains taxed as ordinary income
    - Long-term gains taxed at capital gains rates
    - Selling crypto to offset gains is a valid tax strategy

    IS_PROPERTY = True means wash-sale does NOT apply.
    If/when crypto is reclassified as a security, set IS_PROPERTY = False
    and wash-sale rules will apply.
    """

    # Current classification: True = property (no wash-sale), False = security (wash-sale applies)
    IS_PROPERTY: bool = True

    # Wash-sale rule applies to securities (IRC §1091), not property
    WASH_SALE_APPLIES: bool = not IS_PROPERTY  # = False currently

    NOTE = (
        "Crypto is currently classified as property under IRC §1221. "
        "No wash-sale rule applies. Selling at a loss and immediately re-buying is allowed. "
        "This may change if Congress reclassifies crypto as a security."
    )


class BOND_LADDER:
    """Bond ladder fallback constants used when live Treasury cache is unavailable.

    Live rates are fetched from the Treasury/FRED cache at runtime.
    These static values are used only as a last resort when the cache
    is cold or the market data service is unreachable.

    Update these when the yield curve shifts significantly — roughly
    quarterly or after a major Fed rate decision.
    """

    # Approximate Treasury yields (as of 2025 H1) — update periodically
    FALLBACK_TREASURY_RATES: Dict[str, float] = {
        "1_month": 0.0435,
        "3_month": 0.0430,
        "6_month": 0.0425,
        "1_year": 0.0420,
        "2_year": 0.0410,
        "5_year": 0.0400,
        "10_year": 0.0395,
        "30_year": 0.0410,
    }


class RENTAL:
    """Rental property financial constants and tax rules.

    STR (Short-Term Rental) notes:
    - The STR loophole (IRC §469 material participation) lets real estate
      professionals or materially participating STR owners deduct rental
      losses against ordinary income — bypassing passive activity loss rules.
    - This loophole may be legislated away. STR_LOOPHOLE_ACTIVE controls
      whether the app surfaces this as a recommendation.
    - Average rental period must be <= 7 days to qualify for STR treatment.
    """

    # Toggle this to False if/when Congress closes the STR loophole
    STR_LOOPHOLE_ACTIVE: bool = True

    # Average rental period threshold (days) to qualify as STR under IRC §469
    STR_AVG_RENTAL_DAYS_THRESHOLD: int = 7

    # Residential rental depreciation (27.5-year straight-line, IRC §168)
    RESIDENTIAL_DEPRECIATION_YEARS: float = 27.5
    RESIDENTIAL_DEPRECIATION_RATE: float = 1 / 27.5  # ~3.636% per year

    # Passive activity loss rules for LTR (IRC §469)
    # Losses are passive but up to $25K/yr is allowed if AGI < $100K (active participation)
    PASSIVE_LOSS_ALLOWANCE_MAX: int = 25_000
    PASSIVE_LOSS_PHASEOUT_START: int = 100_000
    PASSIVE_LOSS_PHASEOUT_END: int = 150_000


class DEPENDENT_BENEFITS:
    """Tax benefits and credits for households with dependents (2026 tax year).

    These are per-child/per-dependent amounts. Update each year when IRS
    publishes new limits.

    Sources:
    - Child Tax Credit: IRC §24
    - Child & Dependent Care Credit: IRC §21
    - Dependent Care FSA: IRC §129
    - EITC: IRC §32 (complex income-based formula — amounts below are maximums)
    """

    # Child Tax Credit (IRC §24) — per qualifying child under 17
    CHILD_TAX_CREDIT_PER_CHILD: int = 2_000
    CHILD_TAX_CREDIT_REFUNDABLE_MAX: int = 1_700  # Additional CTC (refundable portion)
    CHILD_TAX_CREDIT_PHASEOUT_SINGLE: int = 200_000
    CHILD_TAX_CREDIT_PHASEOUT_MARRIED: int = 400_000

    # Child & Dependent Care Credit (IRC §21) — for children under 13 or disabled dependents
    DEPENDENT_CARE_CREDIT_MAX_ONE_CHILD: int = 3_000   # max qualifying expenses, 1 child
    DEPENDENT_CARE_CREDIT_MAX_TWO_PLUS: int = 6_000    # max qualifying expenses, 2+ children
    DEPENDENT_CARE_CREDIT_RATE_MAX: float = 0.35        # max credit rate (lower incomes)
    DEPENDENT_CARE_CREDIT_RATE_MIN: float = 0.20        # min credit rate (higher incomes)

    # Dependent Care FSA (IRC §129) — pre-tax dollars for childcare
    DEPENDENT_CARE_FSA_MAX: int = 5_000  # per household (married filing jointly)
    DEPENDENT_CARE_FSA_MAX_SINGLE: int = 5_000

    # Earned Income Tax Credit (EITC) — max amounts by number of children (2026 est.)
    EITC_MAX_NO_CHILD: int = 649
    EITC_MAX_ONE_CHILD: int = 4_328
    EITC_MAX_TWO_CHILDREN: int = 7_152
    EITC_MAX_THREE_PLUS: int = 8_046

    # Age thresholds
    CHILD_TAX_CREDIT_MAX_AGE: int = 17     # must be under 17 at year-end
    DEPENDENT_CARE_MAX_AGE: int = 13       # must be under 13
    QUALIFYING_CHILD_MAX_AGE: int = 19     # or 24 if full-time student
