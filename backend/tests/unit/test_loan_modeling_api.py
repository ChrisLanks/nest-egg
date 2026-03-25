"""Unit tests for loan modeling API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.api.v1.loan_modeling import (
    buy_vs_lease,
    calculate_loan,
    get_amortization_schedule,
)


def _make_user():
    u = Mock()
    u.id = "test-user"
    return u


# ── calculate_loan ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCalculateLoan:
    async def test_basic_mortgage_payment(self):
        """30-year $350k at 6.5% should give ~$2213/mo."""
        result = await calculate_loan(
            principal=350_000,
            annual_rate=0.065,
            term_months=360,
            annual_gross_income=120_000,
            existing_monthly_debt=0,
            current_user=_make_user(),
        )
        assert 2100 < result["monthly_payment"] < 2400
        assert result["total_interest"] > 0
        assert result["total_paid"] > 350_000

    async def test_zero_rate_loan(self):
        """0% interest loan — payment equals principal / months."""
        result = await calculate_loan(
            principal=12_000,
            annual_rate=0.0,
            term_months=12,
            annual_gross_income=60_000,
            existing_monthly_debt=0,
            current_user=_make_user(),
        )
        assert abs(result["monthly_payment"] - 1000.0) < 1

    async def test_dti_included_in_result(self):
        result = await calculate_loan(
            principal=200_000,
            annual_rate=0.07,
            term_months=360,
            annual_gross_income=100_000,
            existing_monthly_debt=500,
            current_user=_make_user(),
        )
        assert "dti" in result
        assert result["dti"]["dti_after"] > 0
        assert result["dti"]["dti_before"] == pytest.approx(0.06, abs=0.01)

    async def test_net_worth_impact_included(self):
        result = await calculate_loan(
            principal=50_000,
            annual_rate=0.05,
            term_months=60,
            annual_gross_income=80_000,
            existing_monthly_debt=0,
            current_user=_make_user(),
        )
        nwi = result["net_worth_impact"]
        assert nwi["debt_added"] == 50_000
        assert nwi["total_interest_cost"] > 0
        assert nwi["monthly_cash_flow_after"] < nwi["monthly_cash_flow_before"]

    async def test_total_paid_equals_monthly_times_term(self):
        result = await calculate_loan(
            principal=10_000,
            annual_rate=0.06,
            term_months=24,
            annual_gross_income=50_000,
            existing_monthly_debt=0,
            current_user=_make_user(),
        )
        expected = result["monthly_payment"] * 24
        assert abs(result["total_paid"] - expected) < 1


# ── get_amortization_schedule ─────────────────────────────────────────────────


@pytest.mark.unit
class TestGetAmortizationSchedule:
    async def test_returns_annual_schedule(self):
        result = await get_amortization_schedule(
            principal=100_000,
            annual_rate=0.06,
            term_months=120,  # 10-year loan
            current_user=_make_user(),
        )
        assert "schedule" in result
        # 10-year loan → 10 annual rows
        assert len(result["schedule"]) == 10

    async def test_ending_balance_approaches_zero(self):
        result = await get_amortization_schedule(
            principal=50_000,
            annual_rate=0.05,
            term_months=60,
            current_user=_make_user(),
        )
        last_year = result["schedule"][-1]
        assert last_year["ending_balance"] < 100  # nearly zero

    async def test_cumulative_interest_increases_monotonically(self):
        result = await get_amortization_schedule(
            principal=200_000,
            annual_rate=0.065,
            term_months=360,
            current_user=_make_user(),
        )
        rows = result["schedule"]
        for i in range(1, len(rows)):
            assert rows[i]["cumulative_interest"] >= rows[i - 1]["cumulative_interest"]

    async def test_principal_paid_increases_over_time(self):
        """Later years should have more principal paid than earlier years."""
        result = await get_amortization_schedule(
            principal=200_000,
            annual_rate=0.065,
            term_months=360,
            current_user=_make_user(),
        )
        rows = result["schedule"]
        assert rows[-1]["principal_paid"] > rows[0]["principal_paid"]

    async def test_monthly_detail_present(self):
        result = await get_amortization_schedule(
            principal=10_000,
            annual_rate=0.06,
            term_months=12,
            current_user=_make_user(),
        )
        assert "months" in result
        assert len(result["months"]) == 12


# ── buy_vs_lease ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBuyVsLease:
    async def test_returns_both_costs(self):
        result = await buy_vs_lease(
            vehicle_price=45_000,
            down_payment=5_000,
            loan_rate=0.059,
            loan_term_months=60,
            lease_monthly=450,
            lease_term_months=36,
            residual_value_pct=0.55,
            current_user=_make_user(),
        )
        assert result["buy_total_cost"] > 0
        assert result["lease_total_cost"] > 0
        assert result["recommendation"] in ("buy", "lease")

    async def test_lease_total_is_monthly_times_term(self):
        result = await buy_vs_lease(
            vehicle_price=40_000,
            down_payment=0,
            loan_rate=0.05,
            loan_term_months=60,
            lease_monthly=400,
            lease_term_months=36,
            residual_value_pct=0.5,
            current_user=_make_user(),
        )
        expected_lease = 400 * 36
        assert abs(result["lease_total_cost"] - expected_lease) < 1

    async def test_savings_equals_absolute_difference(self):
        result = await buy_vs_lease(
            vehicle_price=50_000,
            down_payment=10_000,
            loan_rate=0.06,
            loan_term_months=60,
            lease_monthly=500,
            lease_term_months=36,
            residual_value_pct=0.55,
            current_user=_make_user(),
        )
        assert abs(result["savings"] - abs(result["buy_total_cost"] - result["lease_total_cost"])) < 1

    async def test_high_residual_favors_buy(self):
        """With a very high residual value, buying should be cheaper."""
        result = await buy_vs_lease(
            vehicle_price=40_000,
            down_payment=0,
            loan_rate=0.04,
            loan_term_months=36,
            lease_monthly=600,
            lease_term_months=36,
            residual_value_pct=0.80,  # very high residual
            current_user=_make_user(),
        )
        assert result["recommendation"] == "buy"
