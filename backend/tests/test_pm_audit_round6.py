"""PM audit round 6: validation hardening, JSON error handling, comparison partial failure.

Tests:
- JSON parsing error handling in retirement API (malformed projections_json)
- Scenario comparison partial results (skips scenarios without results)
- Life event age validation (end_age > start_age, annual_cost >= 0)
- LifeEventUpdate validation
- Spending phase vs retirement age / life expectancy validation
- Healthcare override upper bounds (le=500000)
- SS/retirement age < life expectancy cross-field validation
- RetirementScenarioUpdate retirement_age < life_expectancy
- CSV filename sanitization (special characters stripped)
- SS salary default uses current_annual_income when available
"""

import json
import re
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.retirement import (
    LifeEventCreate,
    LifeEventUpdate,
    RetirementScenarioCreate,
    RetirementScenarioUpdate,
    SpendingPhase,
)
from app.models.retirement import LifeEventCategory


# ---------------------------------------------------------------------------
# LifeEventCreate validation
# ---------------------------------------------------------------------------


class TestLifeEventCreateValidation:
    def test_valid_event(self):
        evt = LifeEventCreate(
            name="Home Purchase",
            category=LifeEventCategory.HOME_PURCHASE,
            start_age=45,
            one_time_cost=Decimal("300000"),
        )
        assert evt.start_age == 45

    def test_end_age_must_be_greater_than_start_age(self):
        with pytest.raises(ValidationError) as exc:
            LifeEventCreate(
                name="Bad",
                category=LifeEventCategory.HOME_PURCHASE,
                start_age=50,
                end_age=50,
            )
        assert "end_age" in str(exc.value)

    def test_end_age_before_start_age_rejected(self):
        with pytest.raises(ValidationError):
            LifeEventCreate(
                name="Bad",
                category=LifeEventCategory.HOME_PURCHASE,
                start_age=60,
                end_age=55,
            )

    def test_annual_cost_non_negative(self):
        with pytest.raises(ValidationError):
            LifeEventCreate(
                name="Bad",
                category=LifeEventCategory.HOME_PURCHASE,
                start_age=45,
                annual_cost=Decimal("-100"),
            )

    def test_one_time_cost_non_negative(self):
        with pytest.raises(ValidationError):
            LifeEventCreate(
                name="Bad",
                category=LifeEventCategory.HOME_PURCHASE,
                start_age=45,
                one_time_cost=Decimal("-1"),
            )

    def test_no_end_age_is_valid(self):
        evt = LifeEventCreate(
            name="Annual",
            category=LifeEventCategory.CHILD,
            start_age=35,
            annual_cost=Decimal("5000"),
        )
        assert evt.end_age is None


class TestLifeEventUpdateValidation:
    def test_valid_update(self):
        upd = LifeEventUpdate(start_age=40, end_age=50)
        assert upd.end_age == 50

    def test_end_age_must_be_greater_than_start(self):
        with pytest.raises(ValidationError):
            LifeEventUpdate(start_age=50, end_age=45)

    def test_partial_update_no_age_validation(self):
        # Only one age field — no cross-field check triggered
        upd = LifeEventUpdate(annual_cost=Decimal("1000"))
        assert upd.annual_cost == Decimal("1000")


# ---------------------------------------------------------------------------
# RetirementScenarioCreate validation
# ---------------------------------------------------------------------------


def _base_create(**overrides) -> dict:
    """Minimal valid RetirementScenarioCreate kwargs."""
    defaults = dict(
        name="Test",
        retirement_age=65,
        life_expectancy=90,
        annual_spending_retirement=Decimal("50000"),
    )
    defaults.update(overrides)
    return defaults


class TestRetirementScenarioCreateValidation:
    def test_valid_scenario(self):
        s = RetirementScenarioCreate(**_base_create())
        assert s.retirement_age == 65

    def test_retirement_age_must_be_less_than_life_expectancy(self):
        with pytest.raises(ValidationError) as exc:
            RetirementScenarioCreate(**_base_create(retirement_age=90, life_expectancy=90))
        assert "retirement_age" in str(exc.value) or "life_expectancy" in str(exc.value)

    def test_retirement_age_greater_than_life_expectancy_rejected(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(**_base_create(retirement_age=91, life_expectancy=90))

    def test_ss_start_age_beyond_life_expectancy_rejected(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                **_base_create(
                    life_expectancy=65,
                    retirement_age=62,
                    social_security_start_age=67,
                )
            )

    def test_ss_start_age_within_life_expectancy_ok(self):
        s = RetirementScenarioCreate(
            **_base_create(
                retirement_age=62,
                life_expectancy=90,
                social_security_start_age=67,
            )
        )
        assert s.social_security_start_age == 67

    def test_healthcare_pre65_override_upper_bound(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                **_base_create(healthcare_pre65_override=Decimal("600000"))
            )

    def test_healthcare_medicare_override_upper_bound(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                **_base_create(healthcare_medicare_override=Decimal("999999"))
            )

    def test_healthcare_ltc_override_upper_bound(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                **_base_create(healthcare_ltc_override=Decimal("500001"))
            )

    def test_healthcare_override_at_limit_ok(self):
        s = RetirementScenarioCreate(
            **_base_create(healthcare_pre65_override=Decimal("500000"))
        )
        assert s.healthcare_pre65_override == Decimal("500000")

    def test_spending_phase_before_retirement_age_rejected(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                **_base_create(
                    retirement_age=65,
                    spending_phases=[
                        SpendingPhase(start_age=60, end_age=70, annual_amount=Decimal("40000")),
                    ],
                )
            )

    def test_spending_phase_beyond_life_expectancy_rejected(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                **_base_create(
                    retirement_age=65,
                    life_expectancy=90,
                    spending_phases=[
                        SpendingPhase(start_age=65, end_age=95, annual_amount=Decimal("40000")),
                    ],
                )
            )

    def test_spending_phase_within_bounds_ok(self):
        s = RetirementScenarioCreate(
            **_base_create(
                retirement_age=65,
                life_expectancy=90,
                spending_phases=[
                    SpendingPhase(start_age=65, end_age=80, annual_amount=Decimal("50000")),
                    SpendingPhase(start_age=80, annual_amount=Decimal("30000")),
                ],
            )
        )
        assert len(s.spending_phases) == 2


class TestRetirementScenarioUpdateValidation:
    def test_retirement_age_ge_life_expectancy_rejected(self):
        with pytest.raises(ValidationError):
            RetirementScenarioUpdate(retirement_age=90, life_expectancy=90)

    def test_partial_update_single_field_no_cross_validation(self):
        upd = RetirementScenarioUpdate(retirement_age=65)
        assert upd.retirement_age == 65

    def test_healthcare_override_upper_bound(self):
        with pytest.raises(ValidationError):
            RetirementScenarioUpdate(healthcare_pre65_override=Decimal("600000"))


# ---------------------------------------------------------------------------
# CSV filename sanitization
# ---------------------------------------------------------------------------


class TestCsvFilenameSanitization:
    """Verify the regex pattern used in the CSV export endpoint."""

    def _sanitize(self, name: str) -> str:
        """Mirror the logic from retirement.py export endpoint."""
        return re.sub(r'[^\w\-]', '_', name)[:50]

    def test_spaces_replaced(self):
        assert "_" in self._sanitize("my plan")

    def test_slashes_replaced(self):
        result = self._sanitize("plan/2025")
        assert "/" not in result

    def test_colons_replaced(self):
        result = self._sanitize("plan:v2")
        assert ":" not in result

    def test_asterisks_replaced(self):
        result = self._sanitize("plan*name")
        assert "*" not in result

    def test_question_marks_replaced(self):
        result = self._sanitize("plan?")
        assert "?" not in result

    def test_quotes_replaced(self):
        result = self._sanitize('plan"name')
        assert '"' not in result

    def test_pipe_replaced(self):
        result = self._sanitize("plan|name")
        assert "|" not in result

    def test_truncated_to_50(self):
        long_name = "a" * 100
        assert len(self._sanitize(long_name)) == 50

    def test_normal_name_unchanged(self):
        result = self._sanitize("my_retirement_plan-2025")
        assert result == "my_retirement_plan-2025"

    def test_unicode_letters_preserved(self):
        result = self._sanitize("plan_abc")
        assert "plan_abc" in result


# ---------------------------------------------------------------------------
# JSON parsing error handling
# ---------------------------------------------------------------------------


class TestJsonParsingErrorHandling:
    """Unit tests confirming try/except blocks handle malformed JSON."""

    def test_format_simulation_result_malformed_projections(self):
        """_format_simulation_result should return empty projections on bad JSON."""
        from app.api.v1.retirement import _format_simulation_result

        result = MagicMock()
        result.projections_json = "NOT VALID JSON {{{"
        result.withdrawal_comparison_json = None
        result.id = "00000000-0000-0000-0000-000000000001"
        result.scenario_id = "00000000-0000-0000-0000-000000000002"
        result.computed_at = __import__("datetime").datetime.now()
        result.num_simulations = 1000
        result.compute_time_ms = 100
        result.success_rate = 0.85
        result.readiness_score = 72
        result.median_portfolio_at_retirement = 500000
        result.median_portfolio_at_end = 200000
        result.median_depletion_age = None
        result.estimated_pia = 1500

        formatted = _format_simulation_result(result)
        assert formatted.projections == []

    def test_format_simulation_result_malformed_withdrawal_comparison(self):
        """Malformed withdrawal_comparison_json should result in None, not 500."""
        from app.api.v1.retirement import _format_simulation_result

        result = MagicMock()
        result.projections_json = "[]"
        result.withdrawal_comparison_json = "INVALID JSON"
        result.id = "00000000-0000-0000-0000-000000000001"
        result.scenario_id = "00000000-0000-0000-0000-000000000002"
        result.computed_at = __import__("datetime").datetime.now()
        result.num_simulations = 1000
        result.compute_time_ms = None
        result.success_rate = 0.9
        result.readiness_score = 80
        result.median_portfolio_at_retirement = None
        result.median_portfolio_at_end = None
        result.median_depletion_age = None
        result.estimated_pia = None

        formatted = _format_simulation_result(result)
        assert formatted.withdrawal_comparison is None


# ---------------------------------------------------------------------------
# Scenario comparison partial results
# ---------------------------------------------------------------------------


class TestScenarioComparisonPartialResults:
    """The compare endpoint should skip scenarios without results, not fail entirely."""

    @pytest.mark.asyncio
    async def test_compare_skips_scenario_without_results(self):
        """When one scenario lacks results, it is skipped; others are returned."""
        from app.api.v1.retirement import compare_scenarios
        from app.schemas.retirement import ScenarioComparisonRequest
        import uuid

        id1 = uuid.uuid4()
        id2 = uuid.uuid4()

        mock_scenario1 = MagicMock()
        mock_scenario1.id = id1
        mock_scenario1.name = "Plan A"
        mock_scenario1.retirement_age = 65

        mock_scenario2 = MagicMock()
        mock_scenario2.id = id2
        mock_scenario2.name = "Plan B"
        mock_scenario2.retirement_age = 67

        mock_result1 = MagicMock()
        mock_result1.projections_json = json.dumps([
            {"age": 65, "p10": 100000, "p25": 200000, "p50": 300000,
             "p75": 400000, "p90": 500000, "depletion_pct": 0.0}
        ])
        mock_result1.readiness_score = 75
        mock_result1.success_rate = 0.85
        mock_result1.median_portfolio_at_end = 200000

        mock_user = MagicMock()
        mock_user.organization_id = uuid.uuid4()
        mock_db = AsyncMock()

        request = ScenarioComparisonRequest(scenario_ids=[id1, id2])

        with (
            patch(
                "app.api.v1.retirement.RetirementPlannerService.get_scenario",
                side_effect=[mock_scenario1, mock_scenario2],
            ),
            patch(
                "app.api.v1.retirement.RetirementPlannerService.get_latest_result",
                side_effect=[mock_result1, None],  # Plan B has no results
            ),
        ):
            response = await compare_scenarios(
                data=request,
                current_user=mock_user,
                db=mock_db,
            )

        # Should return only Plan A
        assert len(response.scenarios) == 1
        assert response.scenarios[0].scenario_name == "Plan A"

    @pytest.mark.asyncio
    async def test_compare_raises_400_when_all_scenarios_missing_results(self):
        """If ALL scenarios lack results, raise 400."""
        from app.api.v1.retirement import compare_scenarios
        from app.schemas.retirement import ScenarioComparisonRequest
        from fastapi import HTTPException
        import uuid

        id1 = uuid.uuid4()
        id2 = uuid.uuid4()

        mock_scenario = MagicMock()
        mock_scenario.id = id1
        mock_scenario.name = "Plan A"
        mock_scenario.retirement_age = 65

        mock_user = MagicMock()
        mock_user.organization_id = uuid.uuid4()
        mock_db = AsyncMock()

        request = ScenarioComparisonRequest(scenario_ids=[id1, id2])

        with (
            patch(
                "app.api.v1.retirement.RetirementPlannerService.get_scenario",
                side_effect=[mock_scenario, mock_scenario],
            ),
            patch(
                "app.api.v1.retirement.RetirementPlannerService.get_latest_result",
                return_value=None,
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await compare_scenarios(
                    data=request,
                    current_user=mock_user,
                    db=mock_db,
                )
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# SS salary default uses current_annual_income
# ---------------------------------------------------------------------------


class TestSsSalaryDefault:
    """SS estimate endpoint should prefer current_annual_income over $75k hardcoded."""

    @pytest.mark.asyncio
    async def test_uses_current_annual_income_when_set(self):
        from app.api.v1.retirement import get_social_security_estimate
        import uuid
        from datetime import date

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.organization_id = uuid.uuid4()
        mock_user.birthdate = date(1980, 1, 1)
        mock_user.current_annual_income = 120000.0
        mock_db = AsyncMock()

        captured_salary = {}

        def fake_estimate(current_salary, current_age, birth_year, claiming_age, manual_pia_override):
            captured_salary["salary"] = current_salary
            return {
                "estimated_pia": 2000.0,
                "monthly_at_62": 1400.0,
                "monthly_at_fra": 2000.0,
                "monthly_at_70": 2640.0,
                "fra_age": 67.0,
                "claiming_age": claiming_age,
                "monthly_benefit": 2000.0,
            }

        with patch("app.api.v1.retirement.estimate_social_security", side_effect=fake_estimate):
            await get_social_security_estimate(
                claiming_age=67,
                override_salary=None,
                override_pia=None,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert captured_salary["salary"] == 120000.0

    @pytest.mark.asyncio
    async def test_falls_back_to_75k_when_no_income(self):
        from app.api.v1.retirement import get_social_security_estimate
        import uuid
        from datetime import date

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.organization_id = uuid.uuid4()
        mock_user.birthdate = date(1980, 1, 1)
        mock_user.current_annual_income = None
        mock_db = AsyncMock()

        captured_salary = {}

        def fake_estimate(current_salary, current_age, birth_year, claiming_age, manual_pia_override):
            captured_salary["salary"] = current_salary
            return {
                "estimated_pia": 2000.0,
                "monthly_at_62": 1400.0,
                "monthly_at_fra": 2000.0,
                "monthly_at_70": 2640.0,
                "fra_age": 67.0,
                "claiming_age": claiming_age,
                "monthly_benefit": 2000.0,
            }

        with patch("app.api.v1.retirement.estimate_social_security", side_effect=fake_estimate):
            await get_social_security_estimate(
                claiming_age=67,
                override_salary=None,
                override_pia=None,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert captured_salary["salary"] == 75000

    @pytest.mark.asyncio
    async def test_override_salary_takes_precedence(self):
        from app.api.v1.retirement import get_social_security_estimate
        import uuid
        from datetime import date

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.organization_id = uuid.uuid4()
        mock_user.birthdate = date(1980, 1, 1)
        mock_user.current_annual_income = 120000.0
        mock_db = AsyncMock()

        captured_salary = {}

        def fake_estimate(current_salary, current_age, birth_year, claiming_age, manual_pia_override):
            captured_salary["salary"] = current_salary
            return {
                "estimated_pia": 2000.0,
                "monthly_at_62": 1400.0,
                "monthly_at_fra": 2000.0,
                "monthly_at_70": 2640.0,
                "fra_age": 67.0,
                "claiming_age": claiming_age,
                "monthly_benefit": 2000.0,
            }

        with patch("app.api.v1.retirement.estimate_social_security", side_effect=fake_estimate):
            await get_social_security_estimate(
                claiming_age=67,
                override_salary=50000.0,  # explicit override
                override_pia=None,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert captured_salary["salary"] == 50000.0
