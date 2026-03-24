"""Unit tests for the dependent care FSA and CDCTC optimizer service."""

import pytest

from app.services.dependent_care_optimizer_service import optimize_dependent_care


def _run(**kwargs):
    defaults = dict(
        annual_childcare_expenses=10_000,
        num_dependents=1,
        agi=75_000,
        marginal_rate=0.22,
        filing_status="mfj",
        tax_year=2025,
    )
    defaults.update(kwargs)
    return optimize_dependent_care(**defaults)


@pytest.mark.unit
class TestDcFsaContribution:
    def test_dcfsa_capped_at_expenses_when_below_limit(self):
        result = _run(annual_childcare_expenses=2_000)
        assert result.dcfsa_contribution == pytest.approx(2_000, abs=0.01)

    def test_dcfsa_capped_at_limit_when_expenses_above_limit(self):
        result = _run(annual_childcare_expenses=10_000)
        assert result.dcfsa_contribution == pytest.approx(5_000, abs=0.01)

    def test_mfs_filing_halves_fsa_limit_to_2500(self):
        result = _run(filing_status="mfs", annual_childcare_expenses=10_000)
        assert result.dcfsa_limit == pytest.approx(2_500, abs=0.01)
        assert result.dcfsa_contribution == pytest.approx(2_500, abs=0.01)

    def test_dcfsa_tax_savings_includes_fica(self):
        result = _run(annual_childcare_expenses=5_000, marginal_rate=0.22)
        expected_savings = 5_000 * (0.22 + 0.0765)
        assert result.dcfsa_tax_savings == pytest.approx(expected_savings, abs=0.02)


@pytest.mark.unit
class TestCdctcCalculation:
    def test_cdctc_eligible_expenses_reduced_by_fsa(self):
        result = _run(annual_childcare_expenses=6_000, num_dependents=1)
        # FSA = 5000; cap = 3000; eligible = max(min(6000, 3000) - 5000, 0) = 0
        assert result.cdctc_eligible_expenses == pytest.approx(0.0, abs=0.01)

    def test_cdctc_eligible_with_two_dependents(self):
        # cap is 6000 for 2+; FSA = 5000; eligible = 6000 - 5000 = 1000
        result = _run(annual_childcare_expenses=8_000, num_dependents=2)
        assert result.cdctc_eligible_expenses == pytest.approx(1_000, abs=0.01)

    def test_cdctc_rate_35_pct_for_low_agi(self):
        result = _run(agi=10_000)
        assert result.cdctc_rate == pytest.approx(0.35, abs=0.001)

    def test_cdctc_rate_20_pct_for_high_agi(self):
        result = _run(agi=100_000)
        assert result.cdctc_rate == pytest.approx(0.20, abs=0.001)

    def test_cdctc_rate_phases_down_between_15k_and_43k(self):
        result_low = _run(agi=15_000)
        result_high = _run(agi=43_000)
        assert result_low.cdctc_rate > result_high.cdctc_rate


@pytest.mark.unit
class TestCombinedBenefit:
    def test_combined_benefit_ge_credit_only_and_fsa_only(self):
        result = _run(annual_childcare_expenses=8_000, num_dependents=2, agi=40_000)
        assert result.combined_benefit >= max(result.credit_only_benefit, result.fsa_only_benefit)

    def test_zero_expenses_returns_zero_benefit(self):
        result = _run(annual_childcare_expenses=0)
        assert result.total_benefit == pytest.approx(0.0, abs=0.01)
        assert result.dcfsa_contribution == pytest.approx(0.0, abs=0.01)
        assert result.cdctc_credit == pytest.approx(0.0, abs=0.01)

    def test_two_or_more_dependents_use_higher_expense_cap(self):
        result_one = _run(annual_childcare_expenses=6_000, num_dependents=1)
        result_two = _run(annual_childcare_expenses=6_000, num_dependents=2)
        # With 2 dependents the CDCTC cap is $6k vs $3k for one, so eligible credit is higher
        assert result_two.credit_only_benefit >= result_one.credit_only_benefit

    def test_effective_cost_equals_expenses_minus_total_benefit(self):
        result = _run(annual_childcare_expenses=8_000)
        assert result.effective_childcare_cost == pytest.approx(
            8_000 - result.total_benefit, abs=0.02
        )

    def test_effective_cost_pct_correct(self):
        result = _run(annual_childcare_expenses=8_000)
        expected_pct = result.effective_childcare_cost / 8_000
        assert result.effective_cost_pct == pytest.approx(expected_pct, abs=0.001)

    def test_total_benefit_equals_combined_benefit(self):
        result = _run()
        assert result.total_benefit == result.combined_benefit


@pytest.mark.unit
class TestOutputFields:
    def test_recommendation_is_non_empty(self):
        result = _run()
        assert len(result.recommendation) > 0

    def test_data_note_present(self):
        result = _run()
        assert len(result.data_note) > 10

    def test_inputs_echoed(self):
        result = _run(
            annual_childcare_expenses=7_500,
            num_dependents=2,
            agi=55_000,
            marginal_rate=0.24,
            filing_status="mfj",
            tax_year=2025,
        )
        assert result.annual_childcare_expenses == pytest.approx(7_500)
        assert result.num_dependents == 2
        assert result.agi == pytest.approx(55_000)
        assert result.marginal_rate == pytest.approx(0.24)
        assert result.filing_status == "mfj"
        assert result.tax_year == 2025
