"""Tests for budget suggestion service — _round_up_nice and _suggest_period."""

from app.models.budget import BudgetPeriod
from app.services.budget_suggestion_service import _round_up_nice, _suggest_period


class TestRoundUpNice:
    """Tests for the _round_up_nice helper."""

    def test_zero(self):
        assert _round_up_nice(0) == 0

    def test_negative(self):
        assert _round_up_nice(-10) == 0

    def test_small_amount(self):
        assert _round_up_nice(3.5) == 4

    def test_under_25(self):
        assert _round_up_nice(14) == 15
        assert _round_up_nice(11) == 15

    def test_under_100(self):
        assert _round_up_nice(83) == 90
        assert _round_up_nice(47) == 50

    def test_under_500(self):
        assert _round_up_nice(247) == 250
        assert _round_up_nice(310) == 325

    def test_under_1000(self):
        assert _round_up_nice(510) == 550
        assert _round_up_nice(875) == 900

    def test_over_1000(self):
        assert _round_up_nice(1247) == 1300
        assert _round_up_nice(2050) == 2100

    def test_exact_boundary(self):
        assert _round_up_nice(100) == 100
        assert _round_up_nice(500) == 500
        assert _round_up_nice(1000) == 1000


class TestSuggestPeriod:
    """Tests for the _suggest_period helper."""

    def test_monthly_when_spending_every_month(self):
        """Consistent monthly spending → monthly budget."""
        spending = {f"2025-{m:02d}": 100.0 for m in range(1, 7)}
        result = _suggest_period(100.0, 6, spending)
        assert result == BudgetPeriod.MONTHLY

    def test_semi_annual_when_spending_3_of_6_months(self):
        """Spending in 50% of months → semi-annual."""
        spending = {
            "2025-01": 200.0,
            "2025-02": 0,
            "2025-03": 0,
            "2025-04": 200.0,
            "2025-05": 0,
            "2025-06": 200.0,
        }
        result = _suggest_period(100.0, 6, spending)
        assert result == BudgetPeriod.SEMI_ANNUAL

    def test_quarterly_when_spending_intermittent(self):
        """Spending in ~60% of months → quarterly."""
        spending = {
            "2025-01": 100.0,
            "2025-02": 0,
            "2025-03": 100.0,
            "2025-04": 100.0,
            "2025-05": 0,
        }
        # 3 of 5 months = 60%
        result = _suggest_period(60.0, 5, spending)
        assert result == BudgetPeriod.QUARTERLY

    def test_yearly_when_spending_rarely(self):
        """Spending in ≤25% of months → yearly."""
        spending = {
            "2025-01": 500.0,
            "2025-02": 0,
            "2025-03": 0,
            "2025-04": 0,
            "2025-05": 0,
            "2025-06": 0,
            "2025-07": 0,
            "2025-08": 0,
        }
        # 1 of 8 months = 12.5%
        result = _suggest_period(62.5, 8, spending)
        assert result == BudgetPeriod.YEARLY

    def test_defaults_to_monthly_when_no_data(self):
        result = _suggest_period(0.0, 0, {})
        assert result == BudgetPeriod.MONTHLY

    def test_monthly_with_few_months(self):
        """With only 2 months of data, even sparse spending stays monthly."""
        spending = {"2025-01": 100.0, "2025-02": 0}
        # 1 of 2 = 50%, but month_count < 4 so semi_annual won't trigger
        result = _suggest_period(50.0, 2, spending)
        assert result == BudgetPeriod.MONTHLY

    def test_car_insurance_pattern(self):
        """Car insurance: one large payment every 6 months."""
        spending = {
            "2025-01": 600.0,
            "2025-02": 0,
            "2025-03": 0,
            "2025-04": 0,
            "2025-05": 0,
            "2025-06": 0,
            "2025-07": 600.0,
            "2025-08": 0,
            "2025-09": 0,
            "2025-10": 0,
            "2025-11": 0,
            "2025-12": 0,
        }
        # 2 of 12 = 16.7% → yearly
        result = _suggest_period(100.0, 12, spending)
        assert result == BudgetPeriod.YEARLY

    def test_dentist_pattern(self):
        """Dentist: visits every ~3 months."""
        spending = {
            "2025-01": 150.0,
            "2025-02": 0,
            "2025-03": 0,
            "2025-04": 150.0,
            "2025-05": 0,
            "2025-06": 0,
        }
        # 2 of 6 = 33% → semi_annual
        result = _suggest_period(50.0, 6, spending)
        assert result == BudgetPeriod.SEMI_ANNUAL
