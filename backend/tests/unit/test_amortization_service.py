"""Unit tests for AmortizationService — core financial math."""

import pytest
from datetime import date
from decimal import Decimal

from app.services.amortization_service import AmortizationService


svc = AmortizationService


# ---------------------------------------------------------------------------
# calculate_monthly_payment
# ---------------------------------------------------------------------------


class TestCalculateMonthlyPayment:
    def test_known_loan(self):
        """$200K at 6% for 360 months should yield ~$1199.10."""
        payment = svc.calculate_monthly_payment(
            Decimal("200000"), Decimal("6.0"), 360
        )
        assert Decimal("1199.00") <= payment <= Decimal("1200.00")

    def test_zero_interest(self):
        """0% rate: simple division principal / months."""
        payment = svc.calculate_monthly_payment(
            Decimal("12000"), Decimal("0"), 12
        )
        assert payment == Decimal("1000.00")

    def test_zero_principal(self):
        assert svc.calculate_monthly_payment(Decimal("0"), Decimal("5"), 60) == Decimal("0")

    def test_negative_principal(self):
        assert svc.calculate_monthly_payment(Decimal("-1000"), Decimal("5"), 60) == Decimal("0")

    def test_zero_term(self):
        assert svc.calculate_monthly_payment(Decimal("10000"), Decimal("5"), 0) == Decimal("0")

    def test_short_term_high_rate(self):
        """$1000 at 24% for 12 months."""
        payment = svc.calculate_monthly_payment(
            Decimal("1000"), Decimal("24"), 12
        )
        # Should be roughly $94.56
        assert Decimal("93") <= payment <= Decimal("96")


# ---------------------------------------------------------------------------
# calculate_credit_card_minimum
# ---------------------------------------------------------------------------


class TestCreditCardMinimum:
    def test_floor_applies(self):
        """$500 * 2% = $10 < $25 floor → should return $25."""
        result = svc.calculate_credit_card_minimum(Decimal("500"))
        assert result == Decimal("25.00")

    def test_percentage_exceeds_floor(self):
        """$5000 * 2% = $100 > $25 → should return $100."""
        result = svc.calculate_credit_card_minimum(Decimal("5000"))
        assert result == Decimal("100.00")

    def test_zero_balance(self):
        assert svc.calculate_credit_card_minimum(Decimal("0")) == Decimal("0")

    def test_negative_balance(self):
        assert svc.calculate_credit_card_minimum(Decimal("-100")) == Decimal("0")


# ---------------------------------------------------------------------------
# calculate_payoff_months
# ---------------------------------------------------------------------------


class TestCalculatePayoffMonths:
    def test_zero_interest_simple_division(self):
        months = svc.calculate_payoff_months(
            Decimal("1200"), Decimal("0"), Decimal("100")
        )
        assert months == 12

    def test_payment_less_than_interest(self):
        """$10K at 24%, min $10 → interest ~$200/mo, never pays off."""
        months = svc.calculate_payoff_months(
            Decimal("10000"), Decimal("24"), Decimal("10")
        )
        assert months == 999

    def test_zero_payment(self):
        months = svc.calculate_payoff_months(
            Decimal("1000"), Decimal("10"), Decimal("0")
        )
        assert months == 999

    def test_zero_balance(self):
        months = svc.calculate_payoff_months(
            Decimal("0"), Decimal("10"), Decimal("100")
        )
        assert months == 0

    def test_known_payoff(self):
        """$5000 at 18%, $200/mo — should be roughly 31 months."""
        months = svc.calculate_payoff_months(
            Decimal("5000"), Decimal("18"), Decimal("200")
        )
        assert 28 <= months <= 34


# ---------------------------------------------------------------------------
# generate_amortization_schedule
# ---------------------------------------------------------------------------


class TestAmortizationSchedule:
    def test_final_payment_no_overshoot(self):
        """Final balance should be exactly 0 (no negative overpayment)."""
        schedule = svc.generate_amortization_schedule(
            Decimal("1000"), Decimal("12"), Decimal("200"),
            start_date=date(2025, 1, 15),
        )
        assert schedule[-1]["balance"] == 0.0

    def test_jan31_to_feb_no_crash(self):
        """Start on Jan 31 → Feb should be 28 (not crash on day 31)."""
        schedule = svc.generate_amortization_schedule(
            Decimal("500"), Decimal("0"), Decimal("100"),
            start_date=date(2025, 1, 31),
        )
        # Month 2 should be February 28 (2025 is not a leap year)
        assert schedule[1]["date"] == "2025-02-28"

    def test_preserves_original_day_after_short_month(self):
        """Start Jan 31 → Feb 28 → Mar 31 (recovers original day)."""
        schedule = svc.generate_amortization_schedule(
            Decimal("1000"), Decimal("0"), Decimal("100"),
            start_date=date(2025, 1, 31),
        )
        # March should recover day 31
        assert schedule[2]["date"] == "2025-03-31"

    def test_year_rollover(self):
        """Start Nov 15 → Dec 15 → Jan 15 next year."""
        schedule = svc.generate_amortization_schedule(
            Decimal("500"), Decimal("0"), Decimal("100"),
            start_date=date(2025, 11, 15),
        )
        assert schedule[0]["date"] == "2025-11-15"
        assert schedule[1]["date"] == "2025-12-15"
        assert schedule[2]["date"] == "2026-01-15"

    def test_max_months_cap(self):
        """Schedule should not exceed max_months."""
        schedule = svc.generate_amortization_schedule(
            Decimal("100000"), Decimal("24"), Decimal("100"),
            max_months=10,
        )
        assert len(schedule) <= 10


# ---------------------------------------------------------------------------
# calculate_total_interest
# ---------------------------------------------------------------------------


class TestTotalInterest:
    def test_zero_interest_rate(self):
        """0% rate → total interest = 0."""
        interest = svc.calculate_total_interest(
            Decimal("12000"), Decimal("0"), Decimal("1000")
        )
        assert interest == Decimal("0.00")

    def test_impossible_payoff(self):
        """Payment too low → sentinel 999999."""
        interest = svc.calculate_total_interest(
            Decimal("100000"), Decimal("24"), Decimal("10")
        )
        assert interest == Decimal("999999")

    def test_known_interest(self):
        """$10K at 6% paid $200/mo → total interest should be reasonable."""
        interest = svc.calculate_total_interest(
            Decimal("10000"), Decimal("6"), Decimal("200")
        )
        assert Decimal("500") < interest < Decimal("2500")
