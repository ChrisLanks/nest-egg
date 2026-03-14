"""Unit tests for education planning service."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.services.education_planning_service import EducationPlanningService


@pytest.mark.unit
class TestProject529:
    """Test 529 projection math."""

    @pytest.fixture
    def service(self):
        return EducationPlanningService()

    @pytest.mark.asyncio
    async def test_basic_projection_structure(self, service):
        """Projection returns expected fields."""
        result = await service.project_529(
            current_balance=10000,
            monthly_contribution=200,
            years_until_college=10,
            college_type="public_in_state",
            annual_return=0.06,
        )

        assert "projected_balance" in result
        assert "total_college_cost" in result
        assert "funding_percentage" in result
        assert "funding_gap" in result
        assert "funding_surplus" in result
        assert "recommended_monthly_to_close_gap" in result
        assert "projections" in result
        assert len(result["projections"]) == 10

    @pytest.mark.asyncio
    async def test_compound_growth_with_contributions(self, service):
        """Balance grows via compound interest plus monthly contributions."""
        result = await service.project_529(
            current_balance=10000,
            monthly_contribution=500,
            years_until_college=5,
            college_type="public_in_state",
            annual_return=0.06,
        )

        # Projected balance should exceed initial + contributions
        total_contributions = 10000 + 500 * 12 * 5  # 10000 + 30000 = 40000
        assert result["projected_balance"] > total_contributions

    @pytest.mark.asyncio
    async def test_zero_contribution(self, service):
        """Growth from balance only (no monthly contributions)."""
        result = await service.project_529(
            current_balance=50000,
            monthly_contribution=0,
            years_until_college=10,
            annual_return=0.06,
        )

        # Should grow by compound interest only
        # Approximate: 50000 * (1.06)^10 ≈ 89542
        assert result["projected_balance"] > 50000
        assert result["projected_balance"] < 100000

    @pytest.mark.asyncio
    async def test_zero_balance_with_contributions(self, service):
        """Starting from zero with monthly contributions."""
        result = await service.project_529(
            current_balance=0,
            monthly_contribution=300,
            years_until_college=18,
            annual_return=0.06,
        )

        assert result["current_balance"] == 0
        assert result["projected_balance"] > 0
        # 300/mo for 18 years = $64,800 principal, should be much more with growth
        assert result["projected_balance"] > 64800

    @pytest.mark.asyncio
    async def test_college_cost_inflation(self, service):
        """College costs inflate at 5% annually."""
        result = await service.project_529(
            current_balance=100000,
            monthly_contribution=0,
            years_until_college=10,
            college_type="public_in_state",
            annual_return=0.06,
        )

        # Total college cost should be 4 years of inflated costs
        base_cost = service.COLLEGE_COSTS["public_in_state"]
        inflation = service.COLLEGE_INFLATION_RATE

        expected_total = 0
        for y in range(4):
            expected_total += base_cost * ((1 + inflation) ** (10 + y))
        expected_total = round(expected_total, 2)

        assert result["total_college_cost"] == expected_total

    @pytest.mark.asyncio
    async def test_funding_gap_calculation(self, service):
        """Funding gap is positive when savings < college cost."""
        result = await service.project_529(
            current_balance=1000,
            monthly_contribution=50,
            years_until_college=5,
            college_type="private",
            annual_return=0.06,
        )

        # Private is expensive ($57k/yr), small savings -> gap
        assert result["funding_gap"] > 0
        assert result["funding_surplus"] == 0.0
        assert result["funding_percentage"] < 100

    @pytest.mark.asyncio
    async def test_funding_surplus(self, service):
        """Funding surplus when savings exceed college cost."""
        result = await service.project_529(
            current_balance=500000,
            monthly_contribution=1000,
            years_until_college=5,
            college_type="public_in_state",
            annual_return=0.06,
        )

        # Should have surplus with this much savings
        assert result["funding_surplus"] > 0
        assert result["funding_gap"] == 0.0
        assert result["funding_percentage"] > 100

    @pytest.mark.asyncio
    async def test_recommended_contribution_closes_gap(self, service):
        """Recommended monthly contribution is calculated to close the gap."""
        result = await service.project_529(
            current_balance=10000,
            monthly_contribution=0,
            years_until_college=15,
            college_type="public_in_state",
            annual_return=0.06,
        )

        if result["funding_gap"] > 0:
            assert result["recommended_monthly_to_close_gap"] > 0

            # Verify: if we re-run with the recommended monthly contribution,
            # the gap should be roughly closed
            result2 = await service.project_529(
                current_balance=10000,
                monthly_contribution=result["recommended_monthly_to_close_gap"],
                years_until_college=15,
                college_type="public_in_state",
                annual_return=0.06,
            )
            # The gap should be near zero (within rounding)
            assert result2["funding_gap"] < 100

    @pytest.mark.asyncio
    async def test_different_college_types(self, service):
        """Different college types produce different total costs."""
        results = {}
        for college_type in ("public_in_state", "public_out_of_state", "private"):
            r = await service.project_529(
                current_balance=50000,
                monthly_contribution=200,
                years_until_college=10,
                college_type=college_type,
                annual_return=0.06,
            )
            results[college_type] = r["total_college_cost"]

        # private > out_of_state > in_state
        assert results["private"] > results["public_out_of_state"]
        assert results["public_out_of_state"] > results["public_in_state"]

    @pytest.mark.asyncio
    async def test_unknown_college_type_defaults(self, service):
        """Unknown college type falls back to public_in_state."""
        result = await service.project_529(
            current_balance=10000,
            monthly_contribution=100,
            years_until_college=10,
            college_type="unknown_type",
            annual_return=0.06,
        )

        result_default = await service.project_529(
            current_balance=10000,
            monthly_contribution=100,
            years_until_college=10,
            college_type="public_in_state",
            annual_return=0.06,
        )

        assert result["total_college_cost"] == result_default["total_college_cost"]

    @pytest.mark.asyncio
    async def test_projections_year_by_year_increasing(self, service):
        """Year-by-year projections should be monotonically increasing."""
        result = await service.project_529(
            current_balance=10000,
            monthly_contribution=200,
            years_until_college=10,
            annual_return=0.06,
        )

        projections = result["projections"]
        for i in range(len(projections) - 1):
            assert projections[i + 1]["projected_savings"] > projections[i]["projected_savings"]

    @pytest.mark.asyncio
    async def test_zero_return_rate(self, service):
        """Zero return means growth from contributions only."""
        result = await service.project_529(
            current_balance=10000,
            monthly_contribution=100,
            years_until_college=5,
            annual_return=0.0,
        )

        # Should equal initial + 100 * 60 = 16000
        expected = 10000 + 100 * 12 * 5
        assert abs(result["projected_balance"] - expected) < 1.0

    @pytest.mark.asyncio
    async def test_one_year_horizon(self, service):
        """Single year projection works correctly."""
        result = await service.project_529(
            current_balance=20000,
            monthly_contribution=500,
            years_until_college=1,
            annual_return=0.06,
        )

        assert len(result["projections"]) == 1
        assert result["projections"][0]["year"] == 1
        assert result["projected_balance"] > 20000


@pytest.mark.unit
class TestGetEducationPlans:
    """Test get_education_plans method."""

    @pytest.fixture
    def service(self):
        return EducationPlanningService()

    @pytest.mark.asyncio
    async def test_returns_list(self, service):
        """get_education_plans returns a list for valid org."""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        plans = await service.get_education_plans(
            db=mock_db,
            organization_id=uuid4(),
        )

        assert isinstance(plans, list)
        assert len(plans) == 0
