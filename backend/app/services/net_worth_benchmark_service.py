"""Net worth benchmark service.

Provides peer comparisons using the Federal Reserve's Survey of Consumer
Finances (SCF) 2022 data — the most recent triennial survey. Data is baked
in as constants so there is no external API dependency.

Source: Federal Reserve SCF 2022
https://www.federalreserve.gov/econres/scfindex.htm
"""

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# SCF 2022 median and mean net worth by age group (in 2022 dollars)
# ---------------------------------------------------------------------------

# Keys are age-group labels used in the response.
# Values are (median, mean) tuples in USD.
_SCF_NET_WORTH: dict[str, tuple[int, int]] = {
    "under_35": (39_000, 183_500),
    "35_44": (135_600, 549_600),
    "45_54": (247_200, 975_800),
    "55_64": (364_500, 1_566_900),
    "65_74": (409_900, 1_794_600),
    "75_plus": (335_600, 1_624_100),
}

# SCF 2022 percentile breakpoints by age group.
# Data approximated from SCF public tables and DQYDJ analysis.
# Each entry: [p10, p25, p50, p75, p90] in USD.
_SCF_PERCENTILES: dict[str, list[int]] = {
    "under_35": [-2_400, 3_600, 39_000, 120_000, 300_000],
    "35_44": [0, 21_700, 135_600, 338_000, 836_000],
    "45_54": [2_000, 47_500, 247_200, 695_000, 1_870_000],
    "55_64": [3_400, 63_500, 364_500, 1_054_000, 2_850_000],
    "65_74": [9_400, 78_000, 409_900, 1_100_000, 3_200_000],
    "75_plus": [6_800, 58_000, 335_600, 985_000, 2_680_000],
}

# Human-readable labels for API response
_AGE_GROUP_LABELS: dict[str, str] = {
    "under_35": "Under 35",
    "35_44": "35–44",
    "45_54": "45–54",
    "55_64": "55–64",
    "65_74": "65–74",
    "75_plus": "75+",
}


def _age_to_group(age: int) -> str:
    if age < 35:
        return "under_35"
    if age < 45:
        return "35_44"
    if age < 55:
        return "45_54"
    if age < 65:
        return "55_64"
    if age < 75:
        return "65_74"
    return "75_plus"


def _estimate_percentile(net_worth: float, percentile_breakpoints: list[int]) -> int:
    """Estimate a user's approximate percentile (0-100) via linear interpolation."""
    p10, p25, p50, p75, p90 = percentile_breakpoints

    # Build interpolation segments: (lower_pct, upper_pct, lower_val, upper_val)
    segments = [
        (0, 10, p10 - (p25 - p10), p10),
        (10, 25, p10, p25),
        (25, 50, p25, p50),
        (50, 75, p50, p75),
        (75, 90, p75, p90),
        (90, 100, p90, p90 + (p90 - p75)),
    ]

    for lo_pct, hi_pct, lo_val, hi_val in segments:
        if net_worth <= hi_val or hi_pct == 100:
            if hi_val == lo_val:
                return lo_pct
            ratio = (net_worth - lo_val) / (hi_val - lo_val)
            return max(0, min(100, round(lo_pct + ratio * (hi_pct - lo_pct))))

    return 99


@dataclass
class NetWorthBenchmark:
    age_group: str
    age_group_label: str
    user_net_worth: float
    median_net_worth: int
    mean_net_worth: int
    percentile: int  # approximate percentile rank within age group (0–100)
    # Milestone targets within the age group
    p25: int
    p50: int
    p75: int
    p90: int
    # How far the user is from the next milestone
    next_milestone_label: Optional[str]
    next_milestone_value: Optional[int]
    gap_to_next_milestone: Optional[float]


def compute_benchmark(net_worth: float, age: int) -> NetWorthBenchmark:
    """Compute a net worth benchmark for a user given their net worth and age."""
    group = _age_to_group(age)
    median, mean = _SCF_NET_WORTH[group]
    breakpoints = _SCF_PERCENTILES[group]
    p10, p25, p50, p75, p90 = breakpoints

    percentile = _estimate_percentile(net_worth, breakpoints)

    # Determine next milestone and gap
    milestones = [
        ("25th percentile", p25),
        ("50th percentile (median)", p50),
        ("75th percentile", p75),
        ("90th percentile", p90),
    ]
    next_label: Optional[str] = None
    next_value: Optional[int] = None
    gap: Optional[float] = None

    for label, value in milestones:
        if net_worth < value:
            next_label = label
            next_value = value
            gap = float(value - net_worth)
            break

    return NetWorthBenchmark(
        age_group=group,
        age_group_label=_AGE_GROUP_LABELS[group],
        user_net_worth=net_worth,
        median_net_worth=median,
        mean_net_worth=mean,
        percentile=percentile,
        p25=p25,
        p50=p50,
        p75=p75,
        p90=p90,
        next_milestone_label=next_label,
        next_milestone_value=next_value,
        gap_to_next_milestone=gap,
    )


def get_all_age_group_medians() -> list[dict]:
    """Return median net worth for all age groups (used for context chart)."""
    return [
        {
            "age_group": key,
            "age_group_label": _AGE_GROUP_LABELS[key],
            "median": median,
            "mean": mean,
            "p25": _SCF_PERCENTILES[key][1],
            "p75": _SCF_PERCENTILES[key][3],
        }
        for key, (median, mean) in _SCF_NET_WORTH.items()
    ]
