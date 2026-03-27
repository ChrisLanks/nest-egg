"""Unit tests for charitable giving API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from app.api.v1.charitable_giving import (
    bunching_analysis,
    list_charitable_labels,
)


def _make_user(org_id=None):
    u = Mock()
    u.id = uuid4()
    u.organization_id = org_id or uuid4()
    return u


# ── bunching_analysis ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBunchingAnalysis:
    async def test_annual_giving_below_std_deduction_gives_zero_annual_savings(self):
        """If annual giving < standard deduction, annual strategy saves nothing."""
        result = await bunching_analysis(
            annual_giving=3_000,
            marginal_rate=0.22,
            filing_status="single",
            current_user=_make_user(),
        )
        # standard deduction single = 15000; 3000 < 15000 → no itemized benefit
        assert result["annual_strategy"]["tax_savings_per_year"] == 0.0

    async def test_bunching_two_years_of_giving(self):
        """Bunching doubles giving in year 1 — year1_giving == 2 * annual."""
        result = await bunching_analysis(
            annual_giving=5_000,
            marginal_rate=0.22,
            filing_status="single",
            current_user=_make_user(),
        )
        assert result["bunching_strategy"]["year1_giving"] == pytest.approx(10_000)

    async def test_mfj_uses_higher_standard_deduction(self):
        result_single = await bunching_analysis(
            annual_giving=20_000,
            marginal_rate=0.24,
            filing_status="single",
            current_user=_make_user(),
        )
        result_mfj = await bunching_analysis(
            annual_giving=20_000,
            marginal_rate=0.24,
            filing_status="mfj",
            current_user=_make_user(),
        )
        assert result_mfj["standard_deduction"] > result_single["standard_deduction"]

    async def test_bunching_advantage_positive_when_giving_below_std_ded(self):
        """Below std deduction, bunching every other year has clear advantage."""
        from app.constants.financial import TAX
        std_ded = TAX.STANDARD_DEDUCTION_SINGLE
        # Pick giving so: annual < std_ded, but 2x annual > std_ded
        giving = int(std_ded * 0.6)  # 60% of std ded — doubled = 120% > std ded
        result = await bunching_analysis(
            annual_giving=float(giving),
            marginal_rate=0.22,
            filing_status="single",
            current_user=_make_user(),
        )
        # Bunching year: 2*giving - std_ded benefit; annual: $0 each year
        assert result["bunching_advantage"] > 0

    async def test_annual_strategy_tax_savings_proportional_to_rate(self):
        """Higher marginal rate → higher savings for same giving."""
        result_low = await bunching_analysis(
            annual_giving=20_000,
            marginal_rate=0.22,
            filing_status="single",
            current_user=_make_user(),
        )
        result_high = await bunching_analysis(
            annual_giving=20_000,
            marginal_rate=0.35,
            filing_status="single",
            current_user=_make_user(),
        )
        assert result_high["annual_strategy"]["tax_savings_per_year"] > result_low["annual_strategy"]["tax_savings_per_year"]

    async def test_standard_deduction_single_15000(self):
        from app.api.v1.charitable_giving import STANDARD_DEDUCTION_SINGLE
        result = await bunching_analysis(
            annual_giving=1_000,
            marginal_rate=0.22,
            filing_status="single",
            current_user=_make_user(),
        )
        assert result["standard_deduction"] == STANDARD_DEDUCTION_SINGLE

    async def test_standard_deduction_mfj_30000(self):
        from app.api.v1.charitable_giving import STANDARD_DEDUCTION_MFJ
        result = await bunching_analysis(
            annual_giving=1_000,
            marginal_rate=0.22,
            filing_status="mfj",
            current_user=_make_user(),
        )
        assert result["standard_deduction"] == STANDARD_DEDUCTION_MFJ

    async def test_two_year_bunching_savings_equals_year1_savings(self):
        """Year 2 of bunching uses std deduction (0 savings), so 2-yr total = year1 only."""
        result = await bunching_analysis(
            annual_giving=10_000,
            marginal_rate=0.24,
            filing_status="single",
            current_user=_make_user(),
        )
        assert result["bunching_strategy"]["two_year_savings"] == pytest.approx(
            result["bunching_strategy"]["year1_tax_savings"]
        )


# ── list_charitable_labels ────────────────────────────────────────────────────


@pytest.mark.unit
class TestListCharitableLabels:
    async def test_returns_serialized_labels(self):
        mock_db = AsyncMock()
        user = _make_user()

        label1 = Mock()
        label1.id = uuid4()
        label1.name = "Charity"
        label1.color = "#00AA00"
        label1.is_income = False

        label2 = Mock()
        label2.id = uuid4()
        label2.name = "Donations"
        label2.color = None
        label2.is_income = False

        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = [label1, label2]
        mock_db.execute.return_value = result_mock

        result = await list_charitable_labels(current_user=user, db=mock_db)

        assert len(result) == 2
        assert result[0]["name"] == "Charity"
        assert result[0]["color"] == "#00AA00"
        assert result[1]["name"] == "Donations"
        assert result[1]["color"] is None

    async def test_returns_empty_when_no_labels(self):
        mock_db = AsyncMock()
        user = _make_user()

        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_mock

        result = await list_charitable_labels(current_user=user, db=mock_db)

        assert result == []
