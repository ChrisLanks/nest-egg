"""Tests for Social Security benefit estimator.

Covers:
- FRA (Full Retirement Age) by birth year
- PIA (Primary Insurance Amount) calculation from AIME
- AIME estimation from salary
- Early/delayed claiming age adjustments
- Full estimation integration
"""

import pytest
from app.services.retirement.social_security_estimator import (
    BEND_POINT_1,
    BEND_POINT_2,
    adjust_for_claiming_age,
    estimate_aime_from_salary,
    estimate_pia,
    estimate_social_security,
    get_fra,
)


# ── FRA by birth year ─────────────────────────────────────────────────────────


class TestGetFRA:
    def test_born_1937_or_earlier(self):
        assert get_fra(1935) == 65.0
        assert get_fra(1937) == 65.0

    def test_born_1943_to_1954(self):
        for year in range(1943, 1955):
            assert get_fra(year) == 66.0

    def test_born_1960_or_later(self):
        assert get_fra(1960) == 67.0
        assert get_fra(1990) == 67.0
        assert get_fra(2000) == 67.0

    def test_transitional_years(self):
        # 1938: 65 years 2 months
        assert get_fra(1938) == pytest.approx(65 + 2 / 12, abs=0.01)
        # 1955: 66 years 2 months
        assert get_fra(1955) == pytest.approx(66 + 2 / 12, abs=0.01)
        # 1957: 66 years 6 months
        assert get_fra(1957) == pytest.approx(66.5, abs=0.01)
        # 1959: 66 years 10 months
        assert get_fra(1959) == pytest.approx(66 + 10 / 12, abs=0.01)


# ── PIA from AIME ─────────────────────────────────────────────────────────────


class TestEstimatePIA:
    def test_zero_aime(self):
        assert estimate_pia(0) == 0.0
        assert estimate_pia(-100) == 0.0

    def test_below_first_bend_point(self):
        aime = 1000  # Below $1,174
        expected = 0.90 * 1000
        assert estimate_pia(aime) == pytest.approx(expected, abs=0.01)

    def test_at_first_bend_point(self):
        expected = 0.90 * BEND_POINT_1
        assert estimate_pia(BEND_POINT_1) == pytest.approx(expected, abs=0.01)

    def test_between_bend_points(self):
        aime = 3000
        expected = 0.90 * BEND_POINT_1 + 0.32 * (3000 - BEND_POINT_1)
        assert estimate_pia(aime) == pytest.approx(expected, abs=0.01)

    def test_above_second_bend_point(self):
        aime = 10000
        expected = (
            0.90 * BEND_POINT_1
            + 0.32 * (BEND_POINT_2 - BEND_POINT_1)
            + 0.15 * (10000 - BEND_POINT_2)
        )
        assert estimate_pia(aime) == pytest.approx(expected, abs=0.01)

    def test_known_pia_approximation(self):
        """A $75K salary earner should get roughly $1,800-2,500/mo PIA."""
        aime = estimate_aime_from_salary(75000, 45, 22)
        pia = estimate_pia(aime)
        assert 1000 < pia < 3000


# ── AIME from salary ──────────────────────────────────────────────────────────


class TestEstimateAIME:
    def test_zero_salary(self):
        assert estimate_aime_from_salary(0, 45, 22) == 0.0

    def test_age_at_career_start(self):
        """No years worked should yield zero."""
        assert estimate_aime_from_salary(75000, 22, 22) == 0.0

    def test_positive_salary(self):
        aime = estimate_aime_from_salary(75000, 45, 22)
        assert aime > 0
        # 23 years worked, $75K salary → monthly ~$4K-5K range
        assert 2000 < aime < 8000

    def test_high_salary_capped_per_year(self):
        """Salary above SS taxable max ($168,600) should be capped per year.

        With wage growth backdating, someone earning $300K now had lower
        salary in past years, so many years are under the cap. But the
        AIME with $300K salary should still be higher than $168.6K salary
        (because past years of the $300K earner were higher too).
        """
        aime_high = estimate_aime_from_salary(300000, 45, 22)
        aime_max = estimate_aime_from_salary(168600, 45, 22)
        # Higher salary → higher AIME (past years were proportionally higher)
        assert aime_high > aime_max
        # But not 2x because of the cap on recent years
        assert aime_high < aime_max * 2.0

    def test_longer_career_higher_aime(self):
        aime_short = estimate_aime_from_salary(75000, 30, 22)
        aime_long = estimate_aime_from_salary(75000, 55, 22)
        assert aime_long > aime_short


# ── Claiming age adjustments ──────────────────────────────────────────────────


class TestAdjustForClaimingAge:
    def test_zero_pia(self):
        assert adjust_for_claiming_age(0, 67, 62) == 0.0

    def test_claim_at_fra(self):
        """Claiming at FRA gives the full PIA."""
        pia = 2000
        assert adjust_for_claiming_age(pia, 67, 67) == pytest.approx(2000, abs=0.01)

    def test_early_claiming_reduces(self):
        """Claiming at 62 should be less than PIA."""
        pia = 2000
        at_62 = adjust_for_claiming_age(pia, 67, 62)
        assert at_62 < pia
        # 5 years early from FRA 67: ~30% reduction → ~$1,400
        assert 1200 < at_62 < 1600

    def test_delayed_claiming_increases(self):
        """Claiming at 70 should be more than PIA."""
        pia = 2000
        at_70 = adjust_for_claiming_age(pia, 67, 70)
        assert at_70 > pia
        # 3 years delayed: +24% → ~$2,480
        assert 2300 < at_70 < 2600

    def test_monotonic_increase_with_claiming_age(self):
        """Benefit should increase monotonically from 62 to 70."""
        pia = 2000
        fra = 67
        previous = 0
        for age in range(62, 71):
            benefit = adjust_for_claiming_age(pia, fra, age)
            assert benefit > previous, f"Benefit at {age} ({benefit}) not > at {age - 1} ({previous})"
            previous = benefit

    def test_fra_66(self):
        """Test with FRA=66 (born 1943-1954)."""
        pia = 2000
        at_62 = adjust_for_claiming_age(pia, 66, 62)
        at_fra = adjust_for_claiming_age(pia, 66, 66)
        at_70 = adjust_for_claiming_age(pia, 66, 70)
        assert at_62 < at_fra < at_70


# ── Full SS estimation ────────────────────────────────────────────────────────


class TestEstimateSocialSecurity:
    def test_basic_estimation(self):
        result = estimate_social_security(
            current_salary=75000, current_age=45, birth_year=1980, claiming_age=67
        )
        assert "estimated_pia" in result
        assert "monthly_at_62" in result
        assert "monthly_at_fra" in result
        assert "monthly_at_70" in result
        assert "fra_age" in result
        assert "monthly_benefit" in result

        assert result["estimated_pia"] > 0
        assert result["monthly_at_62"] < result["monthly_at_fra"]
        assert result["monthly_at_fra"] < result["monthly_at_70"]
        assert result["fra_age"] == 67.0

    def test_manual_pia_override(self):
        result = estimate_social_security(
            current_salary=75000, current_age=45, birth_year=1980,
            claiming_age=67, manual_pia_override=2500,
        )
        assert result["estimated_pia"] == 2500
        assert result["monthly_at_fra"] == 2500

    def test_different_birth_years(self):
        """FRA should differ for different birth years."""
        result_1950 = estimate_social_security(
            current_salary=75000, current_age=74, birth_year=1950, claiming_age=67
        )
        result_1980 = estimate_social_security(
            current_salary=75000, current_age=45, birth_year=1980, claiming_age=67
        )
        assert result_1950["fra_age"] == 66.0
        assert result_1980["fra_age"] == 67.0

    def test_claiming_at_62(self):
        result = estimate_social_security(
            current_salary=75000, current_age=45, birth_year=1980, claiming_age=62
        )
        assert result["monthly_benefit"] == result["monthly_at_62"]

    def test_claiming_at_70(self):
        result = estimate_social_security(
            current_salary=75000, current_age=45, birth_year=1980, claiming_age=70
        )
        assert result["monthly_benefit"] == result["monthly_at_70"]
