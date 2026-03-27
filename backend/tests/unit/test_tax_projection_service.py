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
