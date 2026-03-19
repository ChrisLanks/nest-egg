"""Unit tests for FundFeeAnalyzerService.

Tests cover:
- Empty and no-data holdings
- Single holding: ok / high_cost / extreme_cost flags
- Weighted ER calculation
- Annual fee drag computation
- 10/20-year benchmark drag
- Sorting by annual fee descending
- Summary text generation
- Mixed holdings (some with ER, some without)
"""

from __future__ import annotations

import pytest

from app.services.fund_fee_analyzer_service import (
    _BASE_RETURN,
    _BENCHMARK_ER,
    FundFeeAnalysis,
    FundFeeAnalyzerService,
    HoldingFeeDetail,
)

# ── Test helpers ──────────────────────────────────────────────────────────


def _holding(ticker="VTI", name="Total Market", value=10_000.0, er=None):
    """Return a dict-style holding."""
    return {
        "ticker": ticker,
        "name": name,
        "current_total_value": value,
        "expense_ratio": er,
    }


# ── Edge cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_holdings_returns_zero_analysis(self):
        result = FundFeeAnalyzerService.analyze([])
        assert isinstance(result, FundFeeAnalysis)
        assert result.total_invested == 0.0
        assert result.annual_fee_drag == 0.0
        assert result.weighted_avg_expense_ratio == 0.0
        assert result.holdings == []

    def test_all_no_data_holdings(self):
        holdings = [
            _holding("A", er=None, value=10_000),
            _holding("B", er=None, value=20_000),
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings_with_er_data == 0
        assert result.holdings_missing_er_data == 2
        assert result.annual_fee_drag == 0.0
        assert result.weighted_avg_expense_ratio == 0.0

    def test_zero_value_holding_excluded(self):
        holdings = [
            _holding("A", er=0.001, value=0),
            _holding("B", er=0.001, value=10_000),
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.total_invested == 10_000.0
        assert len(result.holdings) == 1

    def test_negative_value_holding_excluded(self):
        result = FundFeeAnalyzerService.analyze([_holding("A", er=0.001, value=-5_000)])
        assert result.total_invested == 0.0


# ── Flag classification ───────────────────────────────────────────────────


class TestFlagClassification:
    def test_low_er_flagged_ok(self):
        holdings = [_holding("VTI", er=0.0003, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings[0].flag == "ok"

    def test_high_cost_threshold_flagged(self):
        """ER of exactly 0.50 % should be flagged high_cost."""
        holdings = [_holding("ACTV", er=0.005, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings[0].flag == "high_cost"

    def test_above_high_cost_threshold_flagged(self):
        holdings = [_holding("ACTV", er=0.007, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings[0].flag == "high_cost"

    def test_extreme_cost_flagged(self):
        """ER >= 1.00 % → extreme_cost."""
        holdings = [_holding("EXPS", er=0.012, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings[0].flag == "extreme_cost"

    def test_no_data_flagged_correctly(self):
        holdings = [_holding("UNK", er=None, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings[0].flag == "no_data"

    def test_high_cost_count_correct(self):
        holdings = [
            _holding("A", er=0.007, value=10_000),  # high_cost
            _holding("B", er=0.015, value=10_000),  # extreme_cost
            _holding("C", er=0.0003, value=10_000),  # ok
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.high_cost_count == 2


# ── Fee math ──────────────────────────────────────────────────────────────


class TestFeeMath:
    def test_annual_fee_is_mv_times_er(self):
        holdings = [_holding("A", er=0.01, value=100_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.annual_fee_drag == pytest.approx(1_000.0, rel=1e-4)

    def test_weighted_er_single_holding(self):
        holdings = [_holding("A", er=0.005, value=50_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.weighted_avg_expense_ratio == pytest.approx(0.005, rel=1e-4)

    def test_weighted_er_two_equal_holdings(self):
        holdings = [
            _holding("A", er=0.001, value=10_000),
            _holding("B", er=0.003, value=10_000),
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.weighted_avg_expense_ratio == pytest.approx(0.002, rel=1e-4)

    def test_weighted_er_skewed_by_larger_holding(self):
        holdings = [
            _holding("A", er=0.001, value=90_000),  # 90% of portfolio
            _holding("B", er=0.010, value=10_000),  # 10% of portfolio
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        expected = (90_000 * 0.001 + 10_000 * 0.010) / 100_000
        assert result.weighted_avg_expense_ratio == pytest.approx(expected, rel=1e-4)

    def test_total_invested_sums_all_values(self):
        holdings = [
            _holding("A", er=0.001, value=30_000),
            _holding("B", er=None, value=20_000),  # no data but still counted
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.total_invested == pytest.approx(50_000.0, rel=1e-4)

    def test_no_data_holding_excluded_from_fee_math(self):
        holdings = [
            _holding("A", er=0.001, value=50_000),
            _holding("B", er=None, value=50_000),
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        # Only holding A contributes to fee drag
        assert result.annual_fee_drag == pytest.approx(50_000 * 0.001, rel=1e-4)


# ── Benchmark drag ────────────────────────────────────────────────────────


class TestBenchmarkDrag:
    def test_er_at_benchmark_gives_zero_drag(self):
        holdings = [_holding("A", er=_BENCHMARK_ER, value=100_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.ten_year_impact_vs_benchmark == 0.0
        assert result.twenty_year_impact_vs_benchmark == 0.0

    def test_er_below_benchmark_gives_zero_drag(self):
        # Should not report negative drag (clamped to 0)
        holdings = [_holding("A", er=0.0001, value=100_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.ten_year_impact_vs_benchmark == 0.0

    def test_higher_er_gives_larger_drag(self):
        h_low = [_holding("A", er=0.001, value=100_000)]
        h_high = [_holding("A", er=0.01, value=100_000)]
        low = FundFeeAnalyzerService.analyze(h_low)
        high = FundFeeAnalyzerService.analyze(h_high)
        assert high.twenty_year_impact_vs_benchmark > low.twenty_year_impact_vs_benchmark

    def test_twenty_year_drag_greater_than_ten(self):
        holdings = [_holding("A", er=0.01, value=100_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.twenty_year_impact_vs_benchmark > result.ten_year_impact_vs_benchmark

    def test_drag_math_manual(self):
        """Verify drag formula: amount*((1+r-bench)^n - (1+r-er)^n)."""
        mv = 100_000
        er = 0.01
        bench = _BENCHMARK_ER
        r = _BASE_RETURN
        n = 10
        expected = mv * (1 + r - bench) ** n - mv * (1 + r - er) ** n
        holdings = [_holding("A", er=er, value=mv)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.ten_year_impact_vs_benchmark == pytest.approx(expected, rel=1e-3)


# ── Sorting ───────────────────────────────────────────────────────────────


class TestSorting:
    def test_holdings_sorted_by_annual_fee_descending(self):
        holdings = [
            _holding("A", er=0.001, value=10_000),  # fee = $10
            _holding("B", er=0.010, value=10_000),  # fee = $100
            _holding("C", er=0.005, value=10_000),  # fee = $50
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        fees = [h.annual_fee for h in result.holdings if h.flag != "no_data"]
        assert fees == sorted(fees, reverse=True)

    def test_no_data_holdings_in_result(self):
        holdings = [
            _holding("A", er=0.01, value=10_000),
            _holding("B", er=None, value=5_000),
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        flags = [h.flag for h in result.holdings]
        assert "no_data" in flags


# ── Per-holding detail ────────────────────────────────────────────────────


class TestHoldingDetail:
    def test_holding_detail_has_correct_fields(self):
        holdings = [_holding("VTI", "Vanguard Total", value=50_000, er=0.0003)]
        result = FundFeeAnalyzerService.analyze(holdings)
        h = result.holdings[0]
        assert isinstance(h, HoldingFeeDetail)
        assert h.ticker == "VTI"
        assert h.name == "Vanguard Total"
        assert h.market_value == pytest.approx(50_000.0, rel=1e-4)
        assert h.expense_ratio == pytest.approx(0.0003, rel=1e-4)

    def test_high_cost_holding_has_suggestion(self):
        holdings = [_holding("COST", er=0.008, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings[0].suggestion is not None
        assert len(result.holdings[0].suggestion) > 0

    def test_ok_holding_has_no_suggestion(self):
        holdings = [_holding("VTI", er=0.0003, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings[0].suggestion is None

    def test_no_data_holding_has_suggestion(self):
        holdings = [_holding("UNK", er=None, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings[0].suggestion is not None

    def test_holding_to_dict_roundtrip(self):
        holdings = [_holding("VTI", er=0.0003, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        d = result.holdings[0].to_dict()
        assert isinstance(d, dict)
        assert "ticker" in d
        assert "annual_fee" in d

    def test_analysis_to_dict_contains_holdings(self):
        holdings = [_holding("VTI", er=0.0003, value=10_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        d = result.to_dict()
        assert "holdings" in d
        assert isinstance(d["holdings"], list)
        assert d["holdings"][0]["ticker"] == "VTI"


# ── Summary text ──────────────────────────────────────────────────────────


class TestSummary:
    def test_summary_non_empty(self):
        holdings = [_holding("A", er=0.001, value=50_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert len(result.summary) > 0

    def test_summary_mentions_annual_drag(self):
        holdings = [_holding("A", er=0.001, value=50_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert "Annual fee drag" in result.summary

    def test_summary_mentions_high_cost_count(self):
        holdings = [_holding("A", er=0.008, value=50_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert "high-cost" in result.summary

    def test_no_data_summary(self):
        holdings = [_holding("A", er=None, value=50_000)]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert "No expense ratio data" in result.summary


# ── ORM object compatibility ──────────────────────────────────────────────


class TestOrmCompatibility:
    """Service must work with ORM-style objects (attribute access) as well as dicts."""

    class _FakeHolding:
        def __init__(self, ticker, name, current_total_value, expense_ratio):
            self.ticker = ticker
            self.name = name
            self.current_total_value = current_total_value
            self.expense_ratio = expense_ratio

    def test_orm_object_input(self):
        holdings = [
            self._FakeHolding("VTI", "Vanguard", 10_000, 0.0003),
            self._FakeHolding("ACTV", "Active Fund", 10_000, 0.008),
        ]
        result = FundFeeAnalyzerService.analyze(holdings)
        assert result.holdings_with_er_data == 2
        assert result.total_invested == pytest.approx(20_000.0)
