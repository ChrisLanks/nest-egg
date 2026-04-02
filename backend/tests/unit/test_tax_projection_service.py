"""Unit tests for TaxProjectionService."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.services.tax_projection_service import (
    TaxProjectionService,
    _ltcg_tax,
    _ordinary_tax,
    _quarterly_schedule,
)

# ── _ordinary_tax ──────────────────────────────────────────────────────────


class TestOrdinaryTax:
    def test_zero_income_no_tax(self):
        tax, breakdown = _ordinary_tax(0.0, "single")
        assert tax == 0.0
        assert breakdown == []

    def test_low_income_lowest_bracket(self):
        tax, breakdown = _ordinary_tax(10_000, "single")
        assert tax > 0
        assert len(breakdown) >= 1
        assert breakdown[0].rate == pytest.approx(0.10, abs=1e-4)

    def test_married_vs_single_different(self):
        tax_s, _ = _ordinary_tax(100_000, "single")
        tax_m, _ = _ordinary_tax(100_000, "married")
        assert tax_m < tax_s

    def test_higher_income_higher_tax(self):
        tax_low, _ = _ordinary_tax(50_000, "single")
        tax_high, _ = _ordinary_tax(200_000, "single")
        assert tax_high > tax_low

    def test_bracket_breakdown_sums_to_total(self):
        total, breakdown = _ordinary_tax(150_000, "single")
        assert sum(b.tax_owed for b in breakdown) == pytest.approx(total, abs=0.05)


# ── _ltcg_tax ─────────────────────────────────────────────────────────────


class TestLtcgTax:
    def test_no_gains_no_tax(self):
        assert _ltcg_tax(0, 50_000, "single") == 0.0

    def test_low_income_zero_rate(self):
        # With very low ordinary income, LTCG may fall in 0% bracket
        tax = _ltcg_tax(10_000, 10_000, "single")
        assert tax >= 0.0

    def test_high_income_15pct_rate(self):
        # Large ordinary income pushes LTCG into 15% bracket
        tax = _ltcg_tax(50_000, 300_000, "single")
        assert tax == pytest.approx(50_000 * 0.15, abs=1.0)

    def test_married_lower_rate_threshold(self):
        # Married filers have higher 0% threshold
        tax_s = _ltcg_tax(30_000, 40_000, "single")
        tax_m = _ltcg_tax(30_000, 40_000, "married")
        assert tax_m <= tax_s


# ── _quarterly_schedule ───────────────────────────────────────────────────


class TestQuarterlySchedule:
    def test_four_payments(self):
        payments = _quarterly_schedule(10_000, date(2025, 6, 1))
        assert len(payments) == 4

    def test_labels(self):
        payments = _quarterly_schedule(10_000, date(2025, 6, 1))
        labels = [p.quarter for p in payments]
        assert labels == ["Q1", "Q2", "Q3", "Q4"]

    def test_total_equals_full_tax(self):
        payments = _quarterly_schedule(10_000, date(2025, 6, 1))
        total = sum(p.amount_due for p in payments)
        assert total == pytest.approx(10_000, abs=0.05)

    def test_q4_due_next_year(self):
        payments = _quarterly_schedule(10_000, date(2025, 6, 1))
        q4 = next(p for p in payments if p.quarter == "Q4")
        assert q4.due_date.startswith("2026")

    def test_zero_tax(self):
        payments = _quarterly_schedule(0, date(2025, 1, 1))
        total = sum(p.amount_due for p in payments)
        assert total == 0.0


# ── TaxProjectionService.project ──────────────────────────────────────────


@pytest.mark.asyncio
class TestTaxProjectionService:
    async def _make_service(self, ytd_income: float = 60_000):
        """Create a TaxProjectionService with a mocked DB."""
        db = AsyncMock()
        svc = TaxProjectionService(db)
        # Mock the _ytd_income method directly
        svc._ytd_income = AsyncMock(return_value=ytd_income)
        return svc

    async def test_basic_projection(self):
        svc = await self._make_service(ytd_income=50_000)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        assert result.tax_year == 2025
        assert result.ordinary_income > 0
        assert result.total_tax_before_credits >= 0

    async def test_annualisation_doubles_half_year(self):
        # July 1 is ~182 days into a 365-day year; annualisation factor ≈ 2.0
        svc = await self._make_service(ytd_income=40_000)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        # Annualised should be roughly 80,000 (±5k for day-of-year precision)
        assert 70_000 < result.ordinary_income < 90_000

    async def test_se_tax_applied(self):
        svc = await self._make_service(ytd_income=0)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            self_employment_income=50_000,
            today=date(2025, 7, 1),
        )
        assert result.se_tax == pytest.approx(50_000 * 0.153, abs=0.01)

    async def test_se_deduction_is_half_se_tax(self):
        svc = await self._make_service(ytd_income=0)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            self_employment_income=50_000,
            today=date(2025, 7, 1),
        )
        assert result.se_deduction == pytest.approx(result.se_tax * 0.5, abs=0.01)

    async def test_ltcg_tax_applied(self):
        svc = await self._make_service(ytd_income=0)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            estimated_capital_gains=50_000,
            today=date(2025, 7, 1),
        )
        assert result.ltcg_tax >= 0

    async def test_standard_deduction_reduces_taxable_income(self):
        svc = await self._make_service(ytd_income=0)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            self_employment_income=30_000,
            today=date(2025, 7, 1),
        )
        assert result.taxable_income < result.ordinary_income

    async def test_married_standard_deduction_larger(self):
        svc_s = await self._make_service(ytd_income=0)
        svc_m = await self._make_service(ytd_income=0)
        result_s = await svc_s.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            self_employment_income=100_000,
            today=date(2025, 7, 1),
        )
        result_m = await svc_m.project(
            organization_id="org-123",
            user_id=None,
            filing_status="married",
            self_employment_income=100_000,
            today=date(2025, 7, 1),
        )
        assert result_m.standard_deduction > result_s.standard_deduction

    async def test_four_quarterly_payments(self):
        svc = await self._make_service(ytd_income=100_000)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        assert len(result.quarterly_payments) == 4

    async def test_total_quarterly_equals_total_tax(self):
        svc = await self._make_service(ytd_income=100_000)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        assert result.total_quarterly_due == pytest.approx(
            result.total_tax_before_credits, abs=0.05
        )

    async def test_safe_harbour_when_prior_year_provided(self):
        svc = await self._make_service(ytd_income=100_000)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            prior_year_tax=20_000,
            today=date(2025, 7, 1),
        )
        # AGI > $150k (annualized ~$200k) → 110% rule applies: $20k * 1.10 = $22k
        assert result.safe_harbour_amount == pytest.approx(22_000, abs=0.01)
        assert result.safe_harbour_met is not None

    async def test_no_safe_harbour_without_prior_year(self):
        svc = await self._make_service(ytd_income=100_000)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        assert result.safe_harbour_amount is None
        assert result.safe_harbour_met is None

    async def test_effective_rate_between_0_and_1(self):
        svc = await self._make_service(ytd_income=60_000)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        assert 0.0 <= result.effective_rate <= 1.0

    async def test_summary_non_empty(self):
        svc = await self._make_service(ytd_income=60_000)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        assert len(result.summary) > 0

    async def test_zero_income_zero_tax(self):
        svc = await self._make_service(ytd_income=0)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        assert result.total_tax_before_credits == pytest.approx(0, abs=1.0)

    # ── Household view / user_id scoping ─────────────────────────────────

    async def test_user_id_forwarded_to_ytd_income(self):
        """When a specific user_id is passed, it must be forwarded to the
        income query so only that member's transactions are included."""
        from uuid import UUID

        user_uuid = UUID("aaaaaaaa-0000-0000-0000-000000000001")
        db = AsyncMock()
        svc = TaxProjectionService(db)
        svc._ytd_income = AsyncMock(return_value=50_000)

        await svc.project(
            organization_id="org-123",
            user_id=user_uuid,
            filing_status="single",
            today=date(2025, 7, 1),
        )

        svc._ytd_income.assert_called_once_with("org-123", user_uuid, 2025)

    async def test_none_user_id_queries_all_members(self):
        """user_id=None means combined household view — query all members."""
        db = AsyncMock()
        svc = TaxProjectionService(db)
        svc._ytd_income = AsyncMock(return_value=100_000)

        await svc.project(
            organization_id="org-456",
            user_id=None,
            filing_status="married",
            today=date(2025, 7, 1),
        )

        svc._ytd_income.assert_called_once_with("org-456", None, 2025)

    async def test_married_filing_positive_taxable_income(self):
        """Married filing with $100k income should yield taxable_income > 0
        and a standard deduction approximately equal to the married IRS value.

        The TAX singleton always reflects the current IRS year (2024: $29,200;
        2025: $30,000; 2026: $32,200).  We check the deduction is larger than
        the single-filer deduction and that taxable income / tax are both > 0.
        """
        svc_single = await self._make_service(ytd_income=0)
        svc_married = await self._make_service(ytd_income=0)

        result_single = await svc_single.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            self_employment_income=100_000,
            today=date(2025, 7, 1),
        )
        result_married = await svc_married.project(
            organization_id="org-123",
            user_id=None,
            filing_status="married",
            self_employment_income=100_000,
            today=date(2025, 7, 1),
        )
        # Married standard deduction must be larger than single
        assert result_married.standard_deduction > result_single.standard_deduction
        # With $100k income the married deduction (~$29-32k) still leaves positive taxable income
        assert result_married.taxable_income > 0
        # Total tax must be positive (and lower than single due to wider brackets + larger deduction)
        assert result_married.total_tax_before_credits > 0
        assert result_married.total_tax_before_credits < result_single.total_tax_before_credits

    async def test_different_user_ids_produce_independent_projections(self):
        """Two different user_ids called separately should produce independent
        projections based on their own income data."""
        from uuid import UUID

        user_a = UUID("aaaaaaaa-0000-0000-0000-000000000001")
        user_b = UUID("bbbbbbbb-0000-0000-0000-000000000002")

        db = AsyncMock()

        svc_a = TaxProjectionService(db)
        svc_a._ytd_income = AsyncMock(return_value=60_000)

        svc_b = TaxProjectionService(db)
        svc_b._ytd_income = AsyncMock(return_value=120_000)

        result_a = await svc_a.project(
            organization_id="org-123",
            user_id=user_a,
            filing_status="single",
            today=date(2025, 7, 1),
        )
        result_b = await svc_b.project(
            organization_id="org-123",
            user_id=user_b,
            filing_status="single",
            today=date(2025, 7, 1),
        )

        assert result_b.ordinary_income > result_a.ordinary_income
        assert result_b.total_tax_before_credits > result_a.total_tax_before_credits


# ── _build_summary ─────────────────────────────────────────────────────────


class TestBuildSummary:
    """Tests for TaxProjectionService._build_summary edge cases."""

    def _make_quarterly(self):
        from app.services.tax_projection_service import QuarterlyPayment
        return [
            QuarterlyPayment(quarter="Q1", due_date="2026-04-15", amount_due=0.0),
            QuarterlyPayment(quarter="Q2", due_date="2026-06-15", amount_due=0.0),
            QuarterlyPayment(quarter="Q3", due_date="2026-09-15", amount_due=0.0),
            QuarterlyPayment(quarter="Q4", due_date="2027-01-15", amount_due=0.0),
        ]

    def test_no_income_tax_state_message_only_for_zero_rate_states(self):
        """States like TX/FL/WA (rate=0.0) should say 'has no state income tax',
        NOT states like CT where income just happens to be below the deduction."""
        quarterly = self._make_quarterly()
        # TX: genuinely no income tax, rate=0 → should say "has no state income tax"
        summary_tx = TaxProjectionService._build_summary(
            ordinary_income=30_000,
            taxable_income=0.0,
            total_tax=0.0,
            effective_rate=0.0,
            marginal_rate=0.10,
            se_tax=0.0,
            ltcg_tax=0.0,
            filing_status="married",
            quarterly=quarterly,
            state="TX",
            state_tax=0.0,
            state_tax_rate=0.0,
        )
        assert "has no state income tax" in summary_tx

    def test_state_with_income_tax_but_zero_taxable_income(self):
        """CT (rate=0.065) with taxable_income=0 should NOT say 'has no state income tax'."""
        quarterly = self._make_quarterly()
        summary_ct = TaxProjectionService._build_summary(
            ordinary_income=27_772,
            taxable_income=0.0,
            total_tax=0.0,
            effective_rate=0.0,
            marginal_rate=0.10,
            se_tax=0.0,
            ltcg_tax=0.0,
            filing_status="married",
            quarterly=quarterly,
            state="CT",
            state_tax=0.0,
            state_tax_rate=0.065,
        )
        assert "has no state income tax" not in summary_ct
        assert "Connecticut" in summary_ct
        assert "deduction" in summary_ct.lower() or "$0" in summary_ct

    def test_state_with_positive_tax_shows_combined(self):
        """When state tax > 0, summary includes combined federal+state total."""
        quarterly = self._make_quarterly()
        summary = TaxProjectionService._build_summary(
            ordinary_income=100_000,
            taxable_income=84_000,
            total_tax=15_000,
            effective_rate=0.15,
            marginal_rate=0.22,
            se_tax=0.0,
            ltcg_tax=0.0,
            filing_status="single",
            quarterly=quarterly,
            state="CA",
            state_tax=8_400,
            state_tax_rate=0.10,
        )
        assert "California" in summary
        assert "Combined" in summary
        assert "$23,400" in summary or "23,400" in summary

    def test_marginal_rate_shown_correctly_when_income_below_deduction(self):
        """When taxable_income=0, marginal rate passed in (10%) should appear in summary."""
        quarterly = self._make_quarterly()
        summary = TaxProjectionService._build_summary(
            ordinary_income=27_772,
            taxable_income=0.0,
            total_tax=0.0,
            effective_rate=0.0,
            marginal_rate=0.10,
            se_tax=0.0,
            ltcg_tax=0.0,
            filing_status="married",
            quarterly=quarterly,
        )
        assert "marginal 10%" in summary


# ── marginal_rate when taxable_income = 0 ─────────────────────────────────


@pytest.mark.asyncio
class TestMarginalRateZeroTaxableIncome:
    async def _make_service(self, ytd_income: float = 0.0):
        from unittest.mock import AsyncMock
        db = AsyncMock()
        svc = TaxProjectionService(db)
        svc._ytd_income = AsyncMock(return_value=ytd_income)
        return svc

    async def test_marginal_rate_is_first_bracket_when_income_below_deduction(self):
        """Married filer with $27,772 income (below $32,200 married deduction in 2026)
        should report marginal_rate = 0.10 (first bracket), not 0.0."""
        svc = await self._make_service(ytd_income=0)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="married",
            self_employment_income=27_772,
            today=date(2025, 7, 1),
        )
        assert result.taxable_income == pytest.approx(0, abs=500)
        # Marginal rate must be the 10% first bracket, not 0
        assert result.marginal_rate == pytest.approx(0.10, abs=0.01)

    async def test_marginal_rate_nonzero_for_single_below_deduction(self):
        """Single filer with income below the standard deduction should also
        show 10% marginal rate (not 0%)."""
        svc = await self._make_service(ytd_income=0)
        result = await svc.project(
            organization_id="org-123",
            user_id=None,
            filing_status="single",
            self_employment_income=10_000,
            today=date(2025, 7, 1),
        )
        # $10k income − SE tax deduction − ~$16,100 standard deduction → taxable = 0
        assert result.taxable_income == pytest.approx(0, abs=1_000)
        assert result.marginal_rate == pytest.approx(0.10, abs=0.01)
