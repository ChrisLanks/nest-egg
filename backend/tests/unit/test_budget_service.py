"""Unit tests for budget service."""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from app.services.budget_service import BudgetService
from app.models.budget import BudgetPeriod


@pytest.mark.unit
class TestBudgetService:
    """Test budget service calculations."""

    def test_calculate_budget_progress_monthly(self):
        """Test monthly budget progress calculation."""
        spent = Decimal("300.00")
        budget_amount = Decimal("500.00")
        period = BudgetPeriod.MONTHLY

        progress = BudgetService._calculate_progress(spent, budget_amount, period)

        assert progress["spent"] == float(spent)
        assert progress["budget"] == float(budget_amount)
        assert progress["remaining"] == float(budget_amount - spent)
        assert progress["percentage"] == 60.0  # 300/500 = 0.6
        assert progress["is_over_budget"] is False

    def test_calculate_budget_progress_over_budget(self):
        """Test budget progress when over budget."""
        spent = Decimal("600.00")
        budget_amount = Decimal("500.00")
        period = BudgetPeriod.MONTHLY

        progress = BudgetService._calculate_progress(spent, budget_amount, period)

        assert progress["percentage"] == 120.0
        assert progress["is_over_budget"] is True
        assert progress["remaining"] == -100.0

    def test_should_send_alert_threshold_exceeded(self):
        """Test alert triggering when threshold exceeded."""
        percentage = 85.0
        threshold = 80.0

        should_alert = BudgetService._should_send_alert(
            percentage,
            threshold,
            last_alert_sent=None
        )

        assert should_alert is True

    def test_should_send_alert_below_threshold(self):
        """Test no alert when below threshold."""
        percentage = 75.0
        threshold = 80.0

        should_alert = BudgetService._should_send_alert(
            percentage,
            threshold,
            last_alert_sent=None
        )

        assert should_alert is False

    def test_should_send_alert_cooldown(self):
        """Test alert cooldown period (24 hours)."""
        percentage = 85.0
        threshold = 80.0
        last_alert = date.today() - timedelta(hours=12)  # 12 hours ago

        should_alert = BudgetService._should_send_alert(
            percentage,
            threshold,
            last_alert_sent=last_alert
        )

        # Should not send again within 24 hours
        assert should_alert is False

    def test_should_send_alert_after_cooldown(self):
        """Test alert can be sent after cooldown."""
        percentage = 85.0
        threshold = 80.0
        last_alert = date.today() - timedelta(days=2)  # 2 days ago

        should_alert = BudgetService._should_send_alert(
            percentage,
            threshold,
            last_alert_sent=last_alert
        )

        # Should send again after 24 hours
        assert should_alert is True

    def test_get_period_date_range_monthly(self):
        """Test date range calculation for monthly period."""
        today = date(2024, 2, 15)

        start_date, end_date = BudgetService._get_period_date_range(
            BudgetPeriod.MONTHLY,
            reference_date=today
        )

        assert start_date == date(2024, 2, 1)
        assert end_date == date(2024, 2, 29)  # 2024 is a leap year

    def test_get_period_date_range_quarterly(self):
        """Test date range calculation for quarterly period."""
        today = date(2024, 2, 15)  # Q1

        start_date, end_date = BudgetService._get_period_date_range(
            BudgetPeriod.QUARTERLY,
            reference_date=today
        )

        assert start_date == date(2024, 1, 1)
        assert end_date == date(2024, 3, 31)

    def test_get_period_date_range_yearly(self):
        """Test date range calculation for yearly period."""
        today = date(2024, 6, 15)

        start_date, end_date = BudgetService._get_period_date_range(
            BudgetPeriod.YEARLY,
            reference_date=today
        )

        assert start_date == date(2024, 1, 1)
        assert end_date == date(2024, 12, 31)
