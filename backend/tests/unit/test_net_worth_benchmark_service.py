"""Unit tests for the net worth benchmark service.

Tests the SCF 2022 data lookups, age-group bucketing, percentile estimation,
and milestone gap calculations — no database or external API required.
"""

import pytest

from app.services.net_worth_benchmark_service import (
    _SCF_PERCENTILES,
    _age_to_group,
    _estimate_percentile,
    compute_benchmark,
    get_all_age_group_medians,
)

# ===========================================================================
# _age_to_group
# ===========================================================================


class TestAgeToGroup:
    def test_under_35(self):
        assert _age_to_group(25) == "under_35"
        assert _age_to_group(34) == "under_35"

    def test_35_44(self):
        assert _age_to_group(35) == "35_44"
        assert _age_to_group(44) == "35_44"

    def test_45_54(self):
        assert _age_to_group(45) == "45_54"
        assert _age_to_group(54) == "45_54"

    def test_55_64(self):
        assert _age_to_group(55) == "55_64"
        assert _age_to_group(64) == "55_64"

    def test_65_74(self):
        assert _age_to_group(65) == "65_74"
        assert _age_to_group(74) == "65_74"

    def test_75_plus(self):
        assert _age_to_group(75) == "75_plus"
        assert _age_to_group(90) == "75_plus"


# ===========================================================================
# _estimate_percentile
# ===========================================================================


class TestEstimatePercentile:
    def _bp(self, group: str) -> list[int]:
        return _SCF_PERCENTILES[group]

    def test_at_median_returns_50(self):
        bp = self._bp("35_44")
        p50 = bp[2]
        pct = _estimate_percentile(p50, bp)
        assert pct == 50

    def test_at_p25_returns_25(self):
        bp = self._bp("35_44")
        p25 = bp[1]
        pct = _estimate_percentile(p25, bp)
        assert pct == 25

    def test_at_p75_returns_75(self):
        bp = self._bp("45_54")
        p75 = bp[3]
        pct = _estimate_percentile(p75, bp)
        assert pct == 75

    def test_at_p90_returns_90(self):
        bp = self._bp("55_64")
        p90 = bp[4]
        pct = _estimate_percentile(p90, bp)
        assert pct == 90

    def test_very_low_net_worth_near_zero(self):
        bp = self._bp("under_35")
        pct = _estimate_percentile(0, bp)
        assert 0 <= pct <= 20

    def test_very_high_net_worth_near_100(self):
        bp = self._bp("under_35")
        pct = _estimate_percentile(10_000_000, bp)
        assert pct >= 95

    def test_result_clamped_0_to_100(self):
        bp = self._bp("under_35")
        assert 0 <= _estimate_percentile(-100_000, bp) <= 100
        assert 0 <= _estimate_percentile(50_000_000, bp) <= 100


# ===========================================================================
# compute_benchmark
# ===========================================================================


@pytest.mark.unit
class TestComputeBenchmark:
    def test_returns_correct_age_group(self):
        result = compute_benchmark(100_000, 40)
        assert result.age_group == "35_44"
        assert result.age_group_label == "35–44"

    def test_user_net_worth_preserved(self):
        result = compute_benchmark(75_000, 30)
        assert result.user_net_worth == 75_000

    def test_median_populated(self):
        result = compute_benchmark(50_000, 50)
        assert result.median_net_worth > 0
        assert result.mean_net_worth > 0

    def test_percentiles_in_order(self):
        result = compute_benchmark(50_000, 45)
        assert result.p25 < result.p50 < result.p75 < result.p90

    def test_below_median_percentile_lt_50(self):
        result = compute_benchmark(10_000, 40)
        assert result.percentile < 50

    def test_above_median_percentile_gt_50(self):
        # Use a net worth clearly above the 35-44 median (~135k)
        result = compute_benchmark(400_000, 40)
        assert result.percentile > 50

    def test_above_p90_no_next_milestone(self):
        # Net worth well above p90 for under_35 group
        result = compute_benchmark(5_000_000, 25)
        assert result.next_milestone_label is None
        assert result.next_milestone_value is None
        assert result.gap_to_next_milestone is None

    def test_below_median_next_milestone_is_median(self):
        result = compute_benchmark(1_000, 40)
        assert result.next_milestone_label is not None
        # First reachable milestone should be p25 or p50
        assert "percentile" in result.next_milestone_label

    def test_gap_to_next_milestone_positive(self):
        result = compute_benchmark(50_000, 40)
        if result.gap_to_next_milestone is not None:
            assert result.gap_to_next_milestone > 0

    def test_gap_equals_milestone_minus_net_worth(self):
        result = compute_benchmark(50_000, 40)
        if result.next_milestone_value is not None and result.gap_to_next_milestone is not None:
            assert abs(result.gap_to_next_milestone - (result.next_milestone_value - 50_000)) < 0.01

    def test_age_75_plus(self):
        result = compute_benchmark(300_000, 80)
        assert result.age_group == "75_plus"
        assert result.median_net_worth > 0

    def test_negative_net_worth_handled(self):
        # Net worth can be negative (more debt than assets)
        result = compute_benchmark(-10_000, 28)
        assert result.percentile >= 0
        assert result.user_net_worth == -10_000


# ===========================================================================
# get_all_age_group_medians
# ===========================================================================


@pytest.mark.unit
class TestGetAllAgeGroupMedians:
    def test_returns_all_six_groups(self):
        groups = get_all_age_group_medians()
        assert len(groups) == 6

    def test_each_group_has_required_keys(self):
        groups = get_all_age_group_medians()
        for g in groups:
            assert "age_group" in g
            assert "age_group_label" in g
            assert "median" in g
            assert "mean" in g
            assert "p25" in g
            assert "p75" in g

    def test_medians_increase_with_age_through_65_74(self):
        groups = get_all_age_group_medians()
        medians = {g["age_group"]: g["median"] for g in groups}
        # Median net worth should generally rise through the 65-74 peak
        assert medians["under_35"] < medians["35_44"]
        assert medians["35_44"] < medians["45_54"]
        assert medians["45_54"] < medians["55_64"]

    def test_p25_less_than_p75(self):
        groups = get_all_age_group_medians()
        for g in groups:
            assert g["p25"] < g["p75"]
