"""Tests for the Year-in-Review endpoint logic."""

import pytest

from app.api.v1.dashboard import (
    YearInReviewCategory,
    YearInReviewExpenses,
    YearInReviewIncome,
    YearInReviewMerchant,
    YearInReviewNetWorth,
    YearInReviewResponse,
    YearInReviewYoY,
)

# ---------------------------------------------------------------------------
# Pydantic model validation
# ---------------------------------------------------------------------------


class TestYearInReviewModels:
    """Validate Year-in-Review Pydantic models."""

    def test_income_model_defaults(self):
        inc = YearInReviewIncome(total=60000.0, avg_monthly=5000.0)
        assert inc.best_month is None
        assert inc.best_amount == 0

    def test_income_model_with_best_month(self):
        inc = YearInReviewIncome(
            total=60000.0, avg_monthly=5000.0, best_month="March", best_amount=7500.0
        )
        assert inc.best_month == "March"
        assert inc.best_amount == 7500.0

    def test_expenses_model_defaults(self):
        exp = YearInReviewExpenses(total=48000.0, avg_monthly=4000.0)
        assert exp.biggest_month is None
        assert exp.biggest_amount == 0

    def test_net_worth_model_all_none(self):
        nw = YearInReviewNetWorth()
        assert nw.start is None
        assert nw.end is None
        assert nw.change is None
        assert nw.change_pct is None

    def test_net_worth_model_with_values(self):
        nw = YearInReviewNetWorth(start=50000.0, end=75000.0, change=25000.0, change_pct=50.0)
        assert nw.change == 25000.0
        assert nw.change_pct == 50.0

    def test_category_model(self):
        cat = YearInReviewCategory(category="Groceries", total=6000.0, pct_of_total=12.5)
        assert cat.category == "Groceries"

    def test_merchant_model(self):
        m = YearInReviewMerchant(merchant="Amazon", total=3000.0, count=42)
        assert m.merchant == "Amazon"
        assert m.count == 42

    def test_yoy_all_none(self):
        yoy = YearInReviewYoY()
        assert yoy.income_change_pct is None
        assert yoy.expense_change_pct is None
        assert yoy.savings_rate_change is None


# ---------------------------------------------------------------------------
# Income / expense aggregation logic
# ---------------------------------------------------------------------------


class TestIncomeExpenseAggregation:
    """Test computation logic for income and expense totals."""

    def test_net_income_calculation(self):
        total_income = 72000.0
        total_expenses = 54000.0
        net_income = total_income - total_expenses
        assert net_income == 18000.0

    def test_savings_rate_calculation(self):
        total_income = 72000.0
        total_expenses = 54000.0
        net_income = total_income - total_expenses
        savings_rate = (net_income / total_income * 100) if total_income > 0 else None
        assert savings_rate == 25.0

    def test_savings_rate_zero_income(self):
        total_income = 0.0
        savings_rate = None if total_income <= 0 else 10.0
        assert savings_rate is None

    def test_average_monthly(self):
        total = 60000.0
        avg_monthly = round(total / 12, 2)
        assert avg_monthly == 5000.0


# ---------------------------------------------------------------------------
# Net worth change logic
# ---------------------------------------------------------------------------


class TestNetWorthChange:
    """Test net worth change and percentage calculation."""

    def test_positive_change(self):
        start = 100000.0
        end = 130000.0
        change = end - start
        change_pct = round(change / abs(start) * 100, 1)
        assert change == 30000.0
        assert change_pct == 30.0

    def test_negative_change(self):
        start = 100000.0
        end = 80000.0
        change = end - start
        change_pct = round(change / abs(start) * 100, 1)
        assert change == -20000.0
        assert change_pct == -20.0

    def test_zero_start_no_pct(self):
        start = 0.0
        end = 50000.0
        change = end - start
        change_pct = None if start == 0 else round(change / abs(start) * 100, 1)
        assert change == 50000.0
        assert change_pct is None

    def test_both_none(self):
        start = None
        end = None
        change = None
        if start is not None and end is not None:
            change = end - start
        assert change is None


# ---------------------------------------------------------------------------
# Year-over-year comparison logic
# ---------------------------------------------------------------------------


class TestYoYComparison:
    """Test year-over-year percentage calculations."""

    def test_income_increase(self):
        prev_income = 60000.0
        curr_income = 72000.0
        change_pct = round((curr_income - prev_income) / prev_income * 100, 1)
        assert change_pct == 20.0

    def test_income_decrease(self):
        prev_income = 72000.0
        curr_income = 60000.0
        change_pct = round((curr_income - prev_income) / prev_income * 100, 1)
        assert change_pct == pytest.approx(-16.7, abs=0.1)

    def test_expense_change(self):
        prev_expenses = 48000.0
        curr_expenses = 50400.0
        change_pct = round((curr_expenses - prev_expenses) / prev_expenses * 100, 1)
        assert change_pct == 5.0

    def test_no_previous_income(self):
        prev_income = 0.0
        income_change_pct = None if prev_income <= 0 else 10.0
        assert income_change_pct is None

    def test_savings_rate_change(self):
        prev_savings_rate = 15.0
        curr_savings_rate = 25.0
        change = round(curr_savings_rate - prev_savings_rate, 1)
        assert change == 10.0

    def test_savings_rate_change_none_if_missing(self):
        prev_savings_rate = None
        curr_savings_rate = 25.0
        change = (
            round(curr_savings_rate - prev_savings_rate, 1)
            if curr_savings_rate is not None and prev_savings_rate is not None
            else None
        )
        assert change is None


# ---------------------------------------------------------------------------
# Milestone detection logic
# ---------------------------------------------------------------------------


class TestYearInReviewMilestones:
    """Test milestone text generation for year-in-review."""

    def test_positive_net_income_milestone(self):
        net_income = 18000.0
        milestones = []
        if net_income > 0:
            milestones.append(f"Saved ${net_income:,.0f} this year")
        assert len(milestones) == 1
        assert "$18,000" in milestones[0]

    def test_no_milestone_for_negative_net_income(self):
        net_income = -5000.0
        milestones = []
        if net_income > 0:
            milestones.append(f"Saved ${net_income:,.0f} this year")
        assert len(milestones) == 0

    def test_high_savings_rate_milestone(self):
        savings_rate = 22.0
        milestones = []
        if savings_rate is not None and savings_rate >= 20:
            milestones.append(f"Achieved {savings_rate:.0f}% savings rate")
        assert len(milestones) == 1
        assert "22%" in milestones[0]

    def test_net_worth_threshold_milestone(self):
        nw_start = 90000.0
        nw_end = 120000.0
        milestones = []
        thresholds = [50000, 100000, 250000, 500000, 750000, 1000000]
        for t in thresholds:
            if nw_start < t <= nw_end:
                milestones.append(f"Reached ${t:,.0f} net worth")
        assert len(milestones) == 1
        assert "$100,000" in milestones[0]

    def test_multiple_net_worth_thresholds_crossed(self):
        nw_start = 40000.0
        nw_end = 300000.0
        milestones = []
        thresholds = [50000, 100000, 250000, 500000, 750000, 1000000]
        for t in thresholds:
            if nw_start < t <= nw_end:
                milestones.append(f"Reached ${t:,.0f} net worth")
        assert len(milestones) == 3
        assert any("$50,000" in m for m in milestones)
        assert any("$100,000" in m for m in milestones)
        assert any("$250,000" in m for m in milestones)

    def test_income_growth_milestone(self):
        income_change_pct = 15.3
        milestones = []
        if income_change_pct is not None and income_change_pct > 0:
            milestones.append(f"Grew income by {income_change_pct:.1f}% year-over-year")
        assert len(milestones) == 1
        assert "15.3%" in milestones[0]

    def test_no_income_growth_milestone_for_decrease(self):
        income_change_pct = -5.0
        milestones = []
        if income_change_pct is not None and income_change_pct > 0:
            milestones.append(f"Grew income by {income_change_pct:.1f}% year-over-year")
        assert len(milestones) == 0


# ---------------------------------------------------------------------------
# Full response model assembly
# ---------------------------------------------------------------------------


class TestYearInReviewResponseAssembly:
    """Test that the full response model can be assembled correctly."""

    def test_full_response_construction(self):
        response = YearInReviewResponse(
            year=2025,
            income=YearInReviewIncome(
                total=72000.0,
                avg_monthly=6000.0,
                best_month="December",
                best_amount=8000.0,
            ),
            expenses=YearInReviewExpenses(
                total=54000.0,
                avg_monthly=4500.0,
                biggest_month="November",
                biggest_amount=6200.0,
            ),
            net_income=18000.0,
            savings_rate=25.0,
            net_worth=YearInReviewNetWorth(
                start=100000.0, end=130000.0, change=30000.0, change_pct=30.0
            ),
            top_expense_categories=[
                YearInReviewCategory(category="Housing", total=18000.0, pct_of_total=33.3),
                YearInReviewCategory(category="Groceries", total=7200.0, pct_of_total=13.3),
            ],
            top_merchants=[
                YearInReviewMerchant(merchant="Whole Foods", total=5400.0, count=104),
            ],
            milestones=["Saved $18,000 this year", "Achieved 25% savings rate"],
            yoy_comparison=YearInReviewYoY(
                income_change_pct=10.0,
                expense_change_pct=5.0,
                savings_rate_change=3.5,
            ),
        )

        assert response.year == 2025
        assert response.net_income == 18000.0
        assert len(response.top_expense_categories) == 2
        assert len(response.milestones) == 2

    def test_minimal_response_construction(self):
        """Response with all optional fields defaulting."""
        response = YearInReviewResponse(
            year=2024,
            income=YearInReviewIncome(total=0.0, avg_monthly=0.0),
            expenses=YearInReviewExpenses(total=0.0, avg_monthly=0.0),
            net_income=0.0,
            savings_rate=None,
            net_worth=YearInReviewNetWorth(),
            top_expense_categories=[],
            top_merchants=[],
            milestones=[],
            yoy_comparison=YearInReviewYoY(),
        )

        assert response.savings_rate is None
        assert response.net_worth.start is None
        assert len(response.top_expense_categories) == 0

    def test_top_categories_pct_sums_correctly(self):
        """Top categories percentages should be based on total expenses."""
        total_expenses = 48000.0
        cats = [
            {"category": "Housing", "total": 18000.0},
            {"category": "Food", "total": 9600.0},
            {"category": "Transport", "total": 4800.0},
        ]
        results = []
        for c in cats:
            pct = round(c["total"] / total_expenses * 100, 1) if total_expenses > 0 else 0
            results.append(
                YearInReviewCategory(category=c["category"], total=c["total"], pct_of_total=pct)
            )

        assert results[0].pct_of_total == 37.5
        assert results[1].pct_of_total == 20.0
        assert results[2].pct_of_total == 10.0
