"""Unit tests for configurable Roth Conversion Headroom target bracket."""

from decimal import Decimal

import pytest

# ── Mirrors TaxBucketService.get_roth_conversion_headroom logic ───────────────

# Simplified brackets for testing (rate, ceiling)
_BRACKETS_SINGLE = [
    (0.10, 12_300),
    (0.12, 49_950),
    (0.22, 106_550),
    (0.24, 203_350),
    (0.32, 258_250),
    (0.35, 645_850),
    (0.37, float("inf")),
]

_BRACKETS_MARRIED = [
    (0.10, 24_600),
    (0.12, 99_900),
    (0.22, 213_100),
    (0.24, 406_700),
    (0.32, 516_500),
    (0.35, 775_100),
    (0.37, float("inf")),
]


def get_roth_conversion_headroom(
    current_income: Decimal,
    filing_status: str,
    target_bracket_rate: Decimal = Decimal("0.22"),
) -> dict:
    """Mirrors TaxBucketService.get_roth_conversion_headroom."""
    brackets = _BRACKETS_MARRIED if filing_status.lower() == "married" else _BRACKETS_SINGLE
    ceiling = Decimal("0")
    for rate, threshold in brackets:
        if Decimal(str(rate)) == target_bracket_rate:
            ceiling = Decimal(str(threshold))
            break
    headroom = max(Decimal("0"), ceiling - current_income)
    return {
        "target_bracket": float(target_bracket_rate),
        "bracket_ceiling": float(ceiling),
        "current_income": float(current_income),
        "conversion_headroom": float(headroom),
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRothConversionHeadroom:
    def test_default_22pct_single(self):
        result = get_roth_conversion_headroom(Decimal("75000"), "single")
        assert result["target_bracket"] == 0.22
        assert result["bracket_ceiling"] == 106_550
        assert abs(result["conversion_headroom"] - 31_550) < 1

    def test_default_22pct_married(self):
        result = get_roth_conversion_headroom(Decimal("75000"), "married")
        assert result["bracket_ceiling"] == 213_100
        assert abs(result["conversion_headroom"] - 138_100) < 1

    def test_configurable_12pct_bracket_single(self):
        result = get_roth_conversion_headroom(
            Decimal("40000"), "single", target_bracket_rate=Decimal("0.12")
        )
        assert result["target_bracket"] == 0.12
        assert result["bracket_ceiling"] == 49_950
        assert abs(result["conversion_headroom"] - 9_950) < 1

    def test_configurable_24pct_bracket_single(self):
        result = get_roth_conversion_headroom(
            Decimal("75000"), "single", target_bracket_rate=Decimal("0.24")
        )
        assert result["target_bracket"] == 0.24
        assert result["bracket_ceiling"] == 203_350
        assert abs(result["conversion_headroom"] - 128_350) < 1

    def test_zero_headroom_when_income_exceeds_ceiling(self):
        # Income above 22% ceiling
        result = get_roth_conversion_headroom(
            Decimal("120000"), "single", target_bracket_rate=Decimal("0.22")
        )
        assert result["conversion_headroom"] == 0.0

    def test_headroom_matches_full_ceiling_when_income_is_zero(self):
        result = get_roth_conversion_headroom(
            Decimal("0"), "single", target_bracket_rate=Decimal("0.22")
        )
        assert abs(result["conversion_headroom"] - 106_550) < 1

    def test_unknown_bracket_returns_zero_ceiling(self):
        # If the target bracket doesn't exist in the table, ceiling stays 0
        result = get_roth_conversion_headroom(
            Decimal("50000"), "single", target_bracket_rate=Decimal("0.99")
        )
        assert result["bracket_ceiling"] == 0.0
        assert result["conversion_headroom"] == 0.0

    def test_married_brackets_wider_than_single(self):
        single = get_roth_conversion_headroom(Decimal("0"), "single")
        married = get_roth_conversion_headroom(Decimal("0"), "married")
        assert married["bracket_ceiling"] > single["bracket_ceiling"]
