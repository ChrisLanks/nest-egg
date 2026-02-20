"""Unit tests for interest accrual task calculation logic."""

import sys
from unittest.mock import MagicMock

# Stub out celery and its full import chain before importing the task module
_celery_stub = MagicMock()
sys.modules.setdefault("celery", _celery_stub)
sys.modules.setdefault("app.workers.celery_app", _celery_stub)

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from app.models.account import Account, AccountType, CompoundingFrequency
from app.workers.tasks.interest_accrual_tasks import _calculate_interest


def _make_account(
    *,
    balance: str,
    rate: str,
    frequency: CompoundingFrequency,
    maturity_date: date | None = None,
    origination_date: date | None = None,
) -> Account:
    """Helper to build a minimal Account mock for interest calculations."""
    account = Mock(spec=Account)
    account.current_balance = Decimal(balance)
    account.interest_rate = Decimal(rate)
    account.compounding_frequency = frequency
    account.maturity_date = maturity_date
    account.origination_date = origination_date
    return account


@pytest.mark.unit
class TestCalculateInterest:
    """Unit tests for _calculate_interest helper."""

    def test_monthly_compounding(self):
        """Monthly: balance × rate / 12."""
        account = _make_account(balance="12000", rate="6", frequency=CompoundingFrequency.MONTHLY)
        result = _calculate_interest(account, date(2024, 3, 1))
        # 12000 × 0.06 / 12 = 60.00
        assert result == Decimal("60.00")

    def test_daily_compounding_march(self):
        """Daily: balance × rate / 365 × days_in_month (31 for March)."""
        account = _make_account(balance="10000", rate="3.65", frequency=CompoundingFrequency.DAILY)
        result = _calculate_interest(account, date(2024, 3, 1))
        # 10000 × 0.0365 / 365 × 31 = 31.00
        expected = Decimal("10000") * Decimal("0.0365") / 365 * 31
        assert abs(result - expected) < Decimal("0.01")

    def test_quarterly_accrues_in_march(self):
        """Quarterly: accrues in Q1 end months (March)."""
        account = _make_account(balance="10000", rate="4", frequency=CompoundingFrequency.QUARTERLY)
        result = _calculate_interest(account, date(2024, 3, 1))
        # 10000 × 0.04 / 4 = 100.00
        assert result == Decimal("100.00")

    def test_quarterly_accrues_in_june(self):
        account = _make_account(balance="10000", rate="4", frequency=CompoundingFrequency.QUARTERLY)
        result = _calculate_interest(account, date(2024, 6, 1))
        assert result == Decimal("100.00")

    def test_quarterly_zero_in_non_quarter_month(self):
        """Quarterly: returns 0 in non-quarter months."""
        account = _make_account(balance="10000", rate="4", frequency=CompoundingFrequency.QUARTERLY)
        result = _calculate_interest(account, date(2024, 2, 1))
        assert result == Decimal("0")

    def test_at_maturity_accrues_on_maturity_month(self):
        """At-maturity: accrues only in the maturity month/year."""
        # Use non-leap-year period: 2022-06-15 to 2023-06-15 = exactly 365 days
        account = _make_account(
            balance="10000",
            rate="5",
            frequency=CompoundingFrequency.AT_MATURITY,
            maturity_date=date(2023, 6, 15),
            origination_date=date(2022, 6, 15),
        )
        result = _calculate_interest(account, date(2023, 6, 1))
        # 365 days × 5% / 365 × 10000 = 500.00
        expected = Decimal("10000") * Decimal("0.05") * 365 / 365
        assert abs(result - expected) < Decimal("0.01")

    def test_at_maturity_zero_before_maturity_month(self):
        """At-maturity: returns 0 if not in maturity month."""
        account = _make_account(
            balance="10000",
            rate="5",
            frequency=CompoundingFrequency.AT_MATURITY,
            maturity_date=date(2024, 12, 1),
            origination_date=date(2023, 12, 1),
        )
        result = _calculate_interest(account, date(2024, 6, 1))
        assert result == Decimal("0")

    def test_at_maturity_no_origination_date_falls_back(self):
        """At-maturity with no origination_date falls back to 1-year simple interest."""
        account = _make_account(
            balance="10000",
            rate="5",
            frequency=CompoundingFrequency.AT_MATURITY,
            maturity_date=date(2024, 6, 15),
            origination_date=None,
        )
        result = _calculate_interest(account, date(2024, 6, 1))
        # fallback: balance * rate = 10000 * 0.05 = 500
        assert result == Decimal("500.00")

    def test_at_maturity_no_maturity_date_returns_zero(self):
        """At-maturity with no maturity_date returns 0."""
        account = _make_account(
            balance="10000",
            rate="5",
            frequency=CompoundingFrequency.AT_MATURITY,
            maturity_date=None,
        )
        result = _calculate_interest(account, date(2024, 6, 1))
        assert result == Decimal("0")

    def test_monthly_zero_rate(self):
        """Zero interest rate produces zero interest."""
        account = _make_account(balance="10000", rate="0", frequency=CompoundingFrequency.MONTHLY)
        result = _calculate_interest(account, date(2024, 3, 1))
        assert result == Decimal("0")

    def test_monthly_large_balance(self):
        """Large balances are handled correctly."""
        account = _make_account(balance="1000000", rate="5", frequency=CompoundingFrequency.MONTHLY)
        result = _calculate_interest(account, date(2024, 1, 1))
        # 1_000_000 × 0.05 / 12 ≈ 4166.67
        assert abs(result - Decimal("4166.67")) < Decimal("0.01")
