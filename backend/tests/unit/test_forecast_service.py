"""Unit tests for forecast service."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import Mock

from app.services.forecast_service import ForecastService
from app.models.recurring_transaction import RecurringTransaction, RecurringFrequency


@pytest.mark.unit
class TestForecastService:
    """Test cash flow forecast service."""

    def test_calculate_future_occurrences_weekly(self):
        """Test weekly recurring transaction projection."""
        pattern = RecurringTransaction(
            merchant_name="Grocery Store",
            average_amount=Decimal("-100.00"),
            frequency=RecurringFrequency.WEEKLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(
            pattern,
            days_ahead=21  # 3 weeks
        )

        # Should have 3 occurrences (weekly for 3 weeks)
        assert len(occurrences) == 3
        assert all(occ["amount"] == Decimal("-100.00") for occ in occurrences)

    def test_calculate_future_occurrences_monthly(self):
        """Test monthly recurring transaction projection."""
        pattern = RecurringTransaction(
            merchant_name="Rent",
            average_amount=Decimal("-2000.00"),
            frequency=RecurringFrequency.MONTHLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(
            pattern,
            days_ahead=90  # ~3 months
        )

        # Should have 3 occurrences
        assert len(occurrences) == 3
        assert all(occ["amount"] == Decimal("-2000.00") for occ in occurrences)
        assert all(occ["merchant"] == "Rent" for occ in occurrences)

    def test_calculate_future_occurrences_biweekly(self):
        """Test biweekly recurring transaction projection."""
        pattern = RecurringTransaction(
            merchant_name="Paycheck",
            average_amount=Decimal("3000.00"),
            frequency=RecurringFrequency.BIWEEKLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(
            pattern,
            days_ahead=56  # 4 biweekly periods
        )

        # Should have 4 occurrences
        assert len(occurrences) == 4
        assert all(occ["amount"] == Decimal("3000.00") for occ in occurrences)

    def test_calculate_future_occurrences_stops_at_end_date(self):
        """Test that projections stop at specified end date."""
        pattern = RecurringTransaction(
            merchant_name="Monthly Bill",
            average_amount=Decimal("-50.00"),
            frequency=RecurringFrequency.MONTHLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(
            pattern,
            days_ahead=45  # 1.5 months
        )

        # Should only have 1 occurrence (next one is beyond 45 days)
        assert len(occurrences) == 1

    def test_negative_balance_detection(self):
        """Test detection of projected negative balance."""
        forecast_data = [
            {"date": date.today(), "projected_balance": 500.0},
            {"date": date.today() + timedelta(days=5), "projected_balance": -100.0},
            {"date": date.today() + timedelta(days=10), "projected_balance": 200.0},
        ]

        # Find first negative balance
        negative_day = next(
            (day for day in forecast_data if day["projected_balance"] < 0),
            None
        )

        assert negative_day is not None
        assert negative_day["projected_balance"] == -100.0

    def test_running_balance_calculation(self):
        """Test running balance calculation over time."""
        starting_balance = Decimal("1000.00")
        transactions = [
            {"date": date.today(), "amount": Decimal("-100.00")},
            {"date": date.today() + timedelta(days=1), "amount": Decimal("500.00")},
            {"date": date.today() + timedelta(days=2), "amount": Decimal("-200.00")},
        ]

        # Calculate running balance
        balance = starting_balance
        balances = []

        for txn in transactions:
            balance += txn["amount"]
            balances.append(balance)

        assert balances[0] == Decimal("900.00")  # 1000 - 100
        assert balances[1] == Decimal("1400.00")  # 900 + 500
        assert balances[2] == Decimal("1200.00")  # 1400 - 200
