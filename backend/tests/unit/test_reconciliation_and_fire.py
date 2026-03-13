"""Tests for ReconciliationResult and FireService pure calculation logic."""

import math
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.fire_service import FireService
from app.services.reconciliation_service import ReconciliationResult

# ---------------------------------------------------------------------------
# ReconciliationResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReconciliationResult:
    """Tests for ReconciliationResult data class."""

    def _make_result(self, **overrides):
        defaults = dict(
            account_id=uuid4(),
            account_name="Checking",
            bank_balance=Decimal("1500.00"),
            computed_balance=Decimal("1450.00"),
            discrepancy=Decimal("50.00"),
            last_synced_at=datetime(2026, 1, 15, 12, 0, 0),
            transaction_count=42,
        )
        defaults.update(overrides)
        return ReconciliationResult(**defaults)

    def test_to_dict_returns_all_fields(self):
        acct_id = uuid4()
        synced = datetime(2026, 3, 1, 8, 30, 0)
        result = ReconciliationResult(
            account_id=acct_id,
            account_name="Savings",
            bank_balance=Decimal("2000.00"),
            computed_balance=Decimal("1900.50"),
            discrepancy=Decimal("99.50"),
            last_synced_at=synced,
            transaction_count=17,
        )
        d = result.to_dict()

        assert d["account_id"] == str(acct_id)
        assert d["account_name"] == "Savings"
        assert d["bank_balance"] == 2000.00
        assert d["computed_balance"] == 1900.50
        assert d["discrepancy"] == 99.50
        assert d["last_synced_at"] == synced.isoformat()
        assert d["transaction_count"] == 17

    def test_to_dict_null_last_synced_at(self):
        result = self._make_result(last_synced_at=None)
        assert result.to_dict()["last_synced_at"] is None

    def test_discrepancy_calculation_positive(self):
        """bank_balance > computed_balance => positive discrepancy."""
        bank = Decimal("1000.00")
        computed = Decimal("950.00")
        discrepancy = bank - computed
        result = self._make_result(
            bank_balance=bank,
            computed_balance=computed,
            discrepancy=discrepancy,
        )
        assert result.to_dict()["discrepancy"] == pytest.approx(50.00)

    def test_discrepancy_calculation_negative(self):
        """bank_balance < computed_balance => negative discrepancy."""
        bank = Decimal("800.00")
        computed = Decimal("850.00")
        discrepancy = bank - computed
        result = self._make_result(
            bank_balance=bank,
            computed_balance=computed,
            discrepancy=discrepancy,
        )
        assert result.to_dict()["discrepancy"] == pytest.approx(-50.00)

    def test_discrepancy_zero_when_balanced(self):
        result = self._make_result(
            bank_balance=Decimal("500.00"),
            computed_balance=Decimal("500.00"),
            discrepancy=Decimal("0.00"),
        )
        assert result.to_dict()["discrepancy"] == 0.0


# ---------------------------------------------------------------------------
# FireService — pure calculation logic (DB calls mocked)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFireServiceCalculations:
    """Tests for FireService calculation methods with mocked data sources."""

    def _make_service(self):
        db = AsyncMock()
        service = FireService.__new__(FireService)
        service.db = db
        service._dashboard_svc = AsyncMock()
        return service

    # -- calculate_years_to_fi --

    @pytest.mark.asyncio
    async def test_years_to_fi_already_fi(self):
        """When current portfolio >= FI number, should report already_fi."""
        service = self._make_service()
        org_id = uuid4()

        service._get_investable_assets = AsyncMock(return_value=Decimal("1500000"))
        service._get_trailing_annual_spending = AsyncMock(return_value=Decimal("50000"))
        service._get_trailing_annual_income = AsyncMock(return_value=Decimal("100000"))

        result = await service.calculate_years_to_fi(org_id)

        assert result["already_fi"] is True
        assert result["years_to_fi"] == 0.0
        # FI number = 50000 / 0.04 = 1_250_000
        assert result["fi_number"] == 1_250_000.0

    @pytest.mark.asyncio
    async def test_years_to_fi_known_inputs(self):
        """Verify formula with known inputs.

        Inputs:
          investable = 200_000, expenses = 40_000, income = 80_000
          withdrawal_rate = 0.04 => fi_number = 1_000_000
          annual_savings = 80_000 - 40_000 = 40_000
          real_return r = 0.07 - 0.03 = 0.04

        Formula (with contributions):
          years = ln((target*r + savings) / (current*r + savings)) / ln(1+r)
          numerator = 1_000_000 * 0.04 + 40_000 = 80_000
          denominator = 200_000 * 0.04 + 40_000 = 48_000
          years = ln(80_000 / 48_000) / ln(1.04)
        """
        service = self._make_service()
        org_id = uuid4()

        service._get_investable_assets = AsyncMock(return_value=Decimal("200000"))
        service._get_trailing_annual_spending = AsyncMock(return_value=Decimal("40000"))
        service._get_trailing_annual_income = AsyncMock(return_value=Decimal("80000"))

        result = await service.calculate_years_to_fi(org_id)

        expected_years = math.log(80_000 / 48_000) / math.log(1.04)
        assert result["years_to_fi"] == round(expected_years, 1)
        assert result["already_fi"] is False
        assert result["fi_number"] == 1_000_000.0
        assert result["annual_savings"] == 40_000.0

    @pytest.mark.asyncio
    async def test_years_to_fi_negative_savings_portfolio_growth_only(self):
        """When savings <= 0 but portfolio exists, should use growth-only formula."""
        service = self._make_service()
        org_id = uuid4()

        service._get_investable_assets = AsyncMock(return_value=Decimal("100000"))
        service._get_trailing_annual_spending = AsyncMock(return_value=Decimal("60000"))
        service._get_trailing_annual_income = AsyncMock(return_value=Decimal("50000"))

        result = await service.calculate_years_to_fi(org_id)

        # fi_number = 60000 / 0.04 = 1_500_000
        # r = 0.04, savings = -10_000 => growth only branch
        expected_years = math.log(1_500_000 / 100_000) / math.log(1.04)
        assert result["years_to_fi"] == round(expected_years, 1)

    @pytest.mark.asyncio
    async def test_years_to_fi_unreachable(self):
        """With no savings and no portfolio, years_to_fi should be None."""
        service = self._make_service()
        org_id = uuid4()

        service._get_investable_assets = AsyncMock(return_value=Decimal("0"))
        service._get_trailing_annual_spending = AsyncMock(return_value=Decimal("40000"))
        service._get_trailing_annual_income = AsyncMock(return_value=Decimal("30000"))

        result = await service.calculate_years_to_fi(org_id)

        assert result["years_to_fi"] is None
        assert result["already_fi"] is False

    # -- calculate_fi_ratio --

    @pytest.mark.asyncio
    async def test_fi_ratio_normal(self):
        service = self._make_service()
        org_id = uuid4()

        service._get_investable_assets = AsyncMock(return_value=Decimal("500000"))
        service._get_trailing_annual_spending = AsyncMock(return_value=Decimal("40000"))

        result = await service.calculate_fi_ratio(org_id)

        # fi_number = 40_000 * 25 = 1_000_000
        # ratio = 500_000 / 1_000_000 = 0.5
        assert result["fi_ratio"] == 0.5
        assert result["fi_number"] == 1_000_000.0

    @pytest.mark.asyncio
    async def test_fi_ratio_zero_expenses(self):
        """With zero expenses, fi_number is 0 and ratio should be 0."""
        service = self._make_service()
        org_id = uuid4()

        service._get_investable_assets = AsyncMock(return_value=Decimal("500000"))
        service._get_trailing_annual_spending = AsyncMock(return_value=Decimal("0"))

        result = await service.calculate_fi_ratio(org_id)

        assert result["fi_ratio"] == 0.0
        assert result["fi_number"] == 0.0

    # -- calculate_savings_rate --

    @pytest.mark.asyncio
    async def test_savings_rate_zero_income(self):
        """With zero income, savings_rate should be 0."""
        service = self._make_service()
        org_id = uuid4()

        service._dashboard_svc.get_spending_and_income = AsyncMock(
            return_value=(Decimal("1000"), Decimal("0"))
        )

        result = await service.calculate_savings_rate(org_id)

        assert result["savings_rate"] == 0.0
        assert result["income"] == 0.0
        assert result["spending"] == 1000.0
        assert result["savings"] == -1000.0

    @pytest.mark.asyncio
    async def test_savings_rate_normal(self):
        service = self._make_service()
        org_id = uuid4()

        service._dashboard_svc.get_spending_and_income = AsyncMock(
            return_value=(Decimal("3000"), Decimal("5000"))
        )

        result = await service.calculate_savings_rate(org_id)

        # savings = 5000 - 3000 = 2000, rate = 2000/5000 = 0.4
        assert result["savings_rate"] == 0.4
        assert result["savings"] == 2000.0
