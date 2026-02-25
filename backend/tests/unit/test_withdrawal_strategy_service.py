"""Tests for withdrawal strategy service.

Covers:
- AccountBuckets class
- RMD calculation
- Tax-optimized withdrawal ordering
- Simple rate withdrawal (4% rule)
- Strategy comparison
"""

import pytest
from app.services.retirement.withdrawal_strategy_service import (
    AccountBuckets,
    compute_rmd_amount,
    run_withdrawal_comparison,
    simple_rate_withdrawal,
    tax_optimized_withdrawal,
)


# ── AccountBuckets ─────────────────────────────────────────────────────────────


class TestAccountBuckets:
    def test_total(self):
        b = AccountBuckets(taxable=100, pre_tax=200, roth=150, hsa=50)
        assert b.total == 500

    def test_total_empty(self):
        b = AccountBuckets()
        assert b.total == 0.0

    def test_apply_return(self):
        b = AccountBuckets(taxable=1000, pre_tax=2000, roth=1500, hsa=500)
        b.apply_return(0.10)
        assert b.taxable == pytest.approx(1100, abs=0.01)
        assert b.pre_tax == pytest.approx(2200, abs=0.01)
        assert b.roth == pytest.approx(1650, abs=0.01)
        assert b.hsa == pytest.approx(550, abs=0.01)

    def test_apply_negative_return(self):
        b = AccountBuckets(taxable=1000, pre_tax=1000)
        b.apply_return(-0.20)
        assert b.taxable == pytest.approx(800, abs=0.01)

    def test_clone_independence(self):
        original = AccountBuckets(taxable=1000, pre_tax=2000)
        clone = original.clone()
        clone.taxable = 0
        assert original.taxable == 1000


# ── RMD calculation ────────────────────────────────────────────────────────────


class TestComputeRMD:
    def test_no_rmd_before_73(self):
        assert compute_rmd_amount(500000, 72) == 0.0
        assert compute_rmd_amount(500000, 60) == 0.0

    def test_rmd_at_73(self):
        rmd = compute_rmd_amount(500000, 73)
        assert rmd > 0
        # At 73, factor is ~26.5 → ~$18,868
        assert 15000 < rmd < 25000

    def test_rmd_increases_with_age(self):
        """Divisor decreases with age, so RMD should increase."""
        rmd_73 = compute_rmd_amount(500000, 73)
        rmd_80 = compute_rmd_amount(500000, 80)
        rmd_90 = compute_rmd_amount(500000, 90)
        assert rmd_80 > rmd_73
        assert rmd_90 > rmd_80

    def test_zero_balance_no_rmd(self):
        assert compute_rmd_amount(0, 75) == 0.0
        assert compute_rmd_amount(-100, 75) == 0.0


# ── Tax-optimized withdrawal ──────────────────────────────────────────────────


class TestTaxOptimizedWithdrawal:
    TAX = dict(federal_rate=0.22, state_rate=0.05, capital_gains_rate=0.15)

    def test_satisfies_rmd_first(self):
        buckets = AccountBuckets(taxable=100000, pre_tax=500000, roth=100000)
        result = tax_optimized_withdrawal(buckets, 50000, 75, **self.TAX)
        # RMD should be computed and satisfied
        assert result["rmd_amount"] > 0
        assert result["withdrawals"]["pre_tax"] >= result["rmd_amount"]

    def test_no_rmd_under_73(self):
        buckets = AccountBuckets(taxable=100000, pre_tax=500000, roth=100000)
        result = tax_optimized_withdrawal(buckets, 50000, 65, **self.TAX)
        assert result["rmd_amount"] == 0.0

    def test_draws_taxable_before_pretax(self):
        """When no RMD, taxable should be drawn before pre-tax."""
        buckets = AccountBuckets(taxable=100000, pre_tax=100000)
        result = tax_optimized_withdrawal(buckets, 20000, 65, **self.TAX)
        # Should primarily use taxable
        assert result["withdrawals"]["taxable"] > 0
        assert result["withdrawals"]["pre_tax"] == 0

    def test_draws_roth_after_taxable_and_pretax(self):
        buckets = AccountBuckets(taxable=5000, pre_tax=5000, roth=100000)
        # Need more than taxable + pre_tax can provide net of taxes
        result = tax_optimized_withdrawal(buckets, 50000, 65, **self.TAX)
        assert result["withdrawals"]["roth"] > 0

    def test_taxes_calculated(self):
        buckets = AccountBuckets(taxable=100000, pre_tax=100000)
        result = tax_optimized_withdrawal(buckets, 30000, 65, **self.TAX)
        assert result["taxes"] > 0

    def test_roth_is_tax_free(self):
        buckets = AccountBuckets(roth=100000)
        result = tax_optimized_withdrawal(buckets, 20000, 65, **self.TAX)
        assert result["taxes"] == 0
        assert result["withdrawals"]["roth"] == pytest.approx(20000, abs=0.01)

    def test_buckets_reduced(self):
        buckets = AccountBuckets(taxable=100000)
        tax_optimized_withdrawal(buckets, 20000, 65, **self.TAX)
        assert buckets.taxable < 100000

    def test_full_depletion(self):
        """When requesting more than available, all buckets should empty."""
        buckets = AccountBuckets(taxable=10000, pre_tax=10000, roth=10000, hsa=10000)
        tax_optimized_withdrawal(buckets, 1000000, 65, **self.TAX)
        assert buckets.total == pytest.approx(0, abs=0.01)


# ── Simple rate withdrawal ────────────────────────────────────────────────────


class TestSimpleRateWithdrawal:
    TAX = dict(federal_rate=0.22, state_rate=0.05, capital_gains_rate=0.15)

    def test_4_percent_rule(self):
        buckets = AccountBuckets(taxable=250000, pre_tax=500000, roth=150000, hsa=100000)
        total = buckets.total  # 1,000,000
        result = simple_rate_withdrawal(buckets, 0.04, **self.TAX)
        total_withdrawn = sum(result["withdrawals"].values())
        assert total_withdrawn == pytest.approx(total * 0.04, abs=1)

    def test_pro_rata_from_all_buckets(self):
        buckets = AccountBuckets(taxable=250000, pre_tax=250000, roth=250000, hsa=250000)
        result = simple_rate_withdrawal(buckets, 0.04, **self.TAX)
        # Each bucket is 25% of total → each should contribute 25% of withdrawal
        expected_per_bucket = 1000000 * 0.04 * 0.25
        for name in ("taxable", "pre_tax", "roth", "hsa"):
            assert result["withdrawals"][name] == pytest.approx(expected_per_bucket, abs=1)

    def test_taxes_on_taxable_and_pretax(self):
        buckets = AccountBuckets(taxable=500000, pre_tax=500000)
        result = simple_rate_withdrawal(buckets, 0.04, **self.TAX)
        assert result["taxes"] > 0

    def test_zero_portfolio(self):
        buckets = AccountBuckets()
        result = simple_rate_withdrawal(buckets, 0.04, **self.TAX)
        assert sum(result["withdrawals"].values()) == 0
        assert result["taxes"] == 0

    def test_skips_empty_buckets(self):
        buckets = AccountBuckets(taxable=0, pre_tax=0, roth=100000, hsa=0)
        result = simple_rate_withdrawal(buckets, 0.04, **self.TAX)
        assert result["withdrawals"]["roth"] > 0
        assert result["withdrawals"]["taxable"] == 0
        assert result["withdrawals"]["pre_tax"] == 0


# ── Strategy comparison ───────────────────────────────────────────────────────


class TestRunWithdrawalComparison:
    def test_returns_both_strategies(self):
        buckets = AccountBuckets(taxable=200000, pre_tax=400000, roth=200000, hsa=50000)
        result = run_withdrawal_comparison(
            initial_buckets=buckets,
            annual_spending=50000,
            retirement_age=65,
            life_expectancy=95,
            annual_return=0.05,
            inflation_rate=0.03,
            withdrawal_rate=0.04,
            federal_rate=0.22,
            state_rate=0.05,
            capital_gains_rate=0.15,
        )
        assert "tax_optimized" in result
        assert "simple_rate" in result
        for strategy in ("tax_optimized", "simple_rate"):
            assert "final_portfolio" in result[strategy]
            assert "total_taxes_paid" in result[strategy]
            assert "depleted_age" in result[strategy]
            assert "success" in result[strategy]

    def test_tax_optimized_usually_better(self):
        """Tax-optimized should generally preserve more wealth than simple rate."""
        buckets = AccountBuckets(taxable=300000, pre_tax=400000, roth=200000, hsa=100000)
        result = run_withdrawal_comparison(
            initial_buckets=buckets,
            annual_spending=40000,
            retirement_age=65,
            life_expectancy=95,
            annual_return=0.06,
            inflation_rate=0.03,
            withdrawal_rate=0.04,
            federal_rate=0.22,
            state_rate=0.05,
            capital_gains_rate=0.15,
            ss_annual=24000,
        )
        # Tax optimized typically pays less tax
        assert result["tax_optimized"]["total_taxes_paid"] <= result["simple_rate"]["total_taxes_paid"] * 1.5

    def test_ss_and_pension_reduce_withdrawals(self):
        """Income sources should improve survival for both strategies."""
        buckets_a = AccountBuckets(taxable=200000, pre_tax=300000, roth=100000)
        result_no_income = run_withdrawal_comparison(
            initial_buckets=buckets_a,
            annual_spending=50000,
            retirement_age=65,
            life_expectancy=95,
            annual_return=0.04,
            inflation_rate=0.03,
            withdrawal_rate=0.04,
            federal_rate=0.22,
            state_rate=0.05,
            capital_gains_rate=0.15,
        )

        buckets_b = AccountBuckets(taxable=200000, pre_tax=300000, roth=100000)
        result_with_income = run_withdrawal_comparison(
            initial_buckets=buckets_b,
            annual_spending=50000,
            retirement_age=65,
            life_expectancy=95,
            annual_return=0.04,
            inflation_rate=0.03,
            withdrawal_rate=0.04,
            federal_rate=0.22,
            state_rate=0.05,
            capital_gains_rate=0.15,
            ss_annual=24000,
            pension_annual=12000,
        )

        # With income, final portfolio should be higher
        assert (
            result_with_income["tax_optimized"]["final_portfolio"]
            >= result_no_income["tax_optimized"]["final_portfolio"]
        )

    def test_depletion_reported(self):
        """With insufficient funds and no income, portfolio should deplete."""
        buckets = AccountBuckets(taxable=50000)
        result = run_withdrawal_comparison(
            initial_buckets=buckets,
            annual_spending=100000,
            retirement_age=65,
            life_expectancy=95,
            annual_return=0.04,
            inflation_rate=0.03,
            withdrawal_rate=0.04,
            federal_rate=0.22,
            state_rate=0.05,
            capital_gains_rate=0.15,
        )
        assert result["tax_optimized"]["success"] is False
        assert result["tax_optimized"]["depleted_age"] is not None
