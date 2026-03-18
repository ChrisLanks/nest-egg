"""Unit tests for spending phases feature.

Tests:
- SpendingPhase schema validation
- Spending phases on Create/Update/Response schemas
- Phase contiguity and overlap validation
- Spending schedule construction from phases
- Fallback to flat spending when no phases
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.retirement import (
    RetirementScenarioCreate,
    RetirementScenarioResponse,
    RetirementScenarioUpdate,
    SpendingPhase,
)

# ---------------------------------------------------------------------------
# SpendingPhase schema
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSpendingPhaseSchema:
    """Test SpendingPhase schema validation."""

    def test_valid_phase(self):
        phase = SpendingPhase(start_age=65, end_age=75, annual_amount=Decimal("100000"))
        assert phase.start_age == 65
        assert phase.end_age == 75
        assert phase.annual_amount == Decimal("100000")

    def test_null_end_age(self):
        phase = SpendingPhase(start_age=70, end_age=None, annual_amount=Decimal("50000"))
        assert phase.end_age is None

    def test_rejects_negative_amount(self):
        with pytest.raises(ValidationError):
            SpendingPhase(start_age=65, end_age=75, annual_amount=Decimal("-1"))

    def test_rejects_zero_amount(self):
        with pytest.raises(ValidationError):
            SpendingPhase(start_age=65, end_age=75, annual_amount=Decimal("0"))

    def test_rejects_start_age_below_min(self):
        with pytest.raises(ValidationError):
            SpendingPhase(start_age=10, end_age=75, annual_amount=Decimal("50000"))

    def test_rejects_start_age_above_max(self):
        with pytest.raises(ValidationError):
            SpendingPhase(start_age=121, end_age=None, annual_amount=Decimal("50000"))


# ---------------------------------------------------------------------------
# Create schema with spending phases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateSchemaSpendingPhases:
    """Test RetirementScenarioCreate with spending_phases."""

    def test_create_without_phases(self):
        data = RetirementScenarioCreate(
            name="No Phases",
            retirement_age=65,
            annual_spending_retirement=Decimal("60000"),
        )
        assert data.spending_phases is None

    def test_create_with_valid_phases(self):
        data = RetirementScenarioCreate(
            name="With Phases",
            retirement_age=65,
            annual_spending_retirement=Decimal("60000"),
            spending_phases=[
                SpendingPhase(start_age=65, end_age=75, annual_amount=Decimal("150000")),
                SpendingPhase(start_age=75, end_age=None, annual_amount=Decimal("50000")),
            ],
        )
        assert data.spending_phases is not None
        assert len(data.spending_phases) == 2

    def test_create_with_single_phase(self):
        data = RetirementScenarioCreate(
            name="Single Phase",
            retirement_age=65,
            annual_spending_retirement=Decimal("60000"),
            spending_phases=[
                SpendingPhase(start_age=65, end_age=None, annual_amount=Decimal("80000")),
            ],
        )
        assert len(data.spending_phases) == 1

    def test_rejects_overlapping_phases(self):
        with pytest.raises(ValidationError, match="contiguous"):
            RetirementScenarioCreate(
                name="Overlap",
                retirement_age=65,
                annual_spending_retirement=Decimal("60000"),
                spending_phases=[
                    SpendingPhase(start_age=65, end_age=80, annual_amount=Decimal("100000")),
                    SpendingPhase(start_age=75, end_age=None, annual_amount=Decimal("50000")),
                ],
            )

    def test_rejects_gap_between_phases(self):
        with pytest.raises(ValidationError, match="contiguous"):
            RetirementScenarioCreate(
                name="Gap",
                retirement_age=65,
                annual_spending_retirement=Decimal("60000"),
                spending_phases=[
                    SpendingPhase(start_age=65, end_age=70, annual_amount=Decimal("100000")),
                    SpendingPhase(start_age=75, end_age=None, annual_amount=Decimal("50000")),
                ],
            )

    def test_rejects_null_end_age_on_non_last_phase(self):
        with pytest.raises(ValidationError, match="last spending phase"):
            RetirementScenarioCreate(
                name="Bad Null",
                retirement_age=65,
                annual_spending_retirement=Decimal("60000"),
                spending_phases=[
                    SpendingPhase(start_age=65, end_age=None, annual_amount=Decimal("100000")),
                    SpendingPhase(start_age=75, end_age=None, annual_amount=Decimal("50000")),
                ],
            )

    def test_rejects_end_age_less_than_start(self):
        with pytest.raises(ValidationError, match="greater than"):
            RetirementScenarioCreate(
                name="Bad Range",
                retirement_age=65,
                annual_spending_retirement=Decimal("60000"),
                spending_phases=[
                    SpendingPhase(start_age=75, end_age=65, annual_amount=Decimal("100000")),
                ],
            )

    def test_phases_auto_sorted_by_start_age(self):
        """Phases provided in wrong order should be sorted."""
        data = RetirementScenarioCreate(
            name="Sorted",
            retirement_age=65,
            annual_spending_retirement=Decimal("60000"),
            spending_phases=[
                SpendingPhase(start_age=75, end_age=None, annual_amount=Decimal("50000")),
                SpendingPhase(start_age=65, end_age=75, annual_amount=Decimal("100000")),
            ],
        )
        assert data.spending_phases[0].start_age == 65
        assert data.spending_phases[1].start_age == 75


# ---------------------------------------------------------------------------
# Update schema with spending phases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateSchemaSpendingPhases:
    """Test RetirementScenarioUpdate with spending_phases."""

    def test_update_with_phases(self):
        data = RetirementScenarioUpdate(
            spending_phases=[
                SpendingPhase(start_age=67, end_age=80, annual_amount=Decimal("120000")),
                SpendingPhase(start_age=80, end_age=None, annual_amount=Decimal("60000")),
            ]
        )
        assert data.spending_phases is not None
        assert len(data.spending_phases) == 2

    def test_update_clear_phases_with_none(self):
        data = RetirementScenarioUpdate(spending_phases=None)
        assert data.spending_phases is None

    def test_update_exclude_unset_omits_phases(self):
        data = RetirementScenarioUpdate(name="Renamed")
        dumped = data.model_dump(exclude_unset=True)
        assert "spending_phases" not in dumped

    def test_update_exclude_unset_includes_phases_when_set(self):
        data = RetirementScenarioUpdate(
            spending_phases=[
                SpendingPhase(start_age=65, end_age=None, annual_amount=Decimal("80000")),
            ]
        )
        dumped = data.model_dump(exclude_unset=True)
        assert "spending_phases" in dumped


# ---------------------------------------------------------------------------
# Response schema parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResponseSchemaSpendingPhases:
    """Test RetirementScenarioResponse parses spending_phases."""

    def test_response_parses_json_string(self):
        """spending_phases as JSON string should be parsed to list."""
        json_str = '[{"start_age": 65, "end_age": 75, "annual_amount": 100000}]'
        assert "spending_phases" in RetirementScenarioResponse.model_fields
        # Test the field_validator directly
        parsed = RetirementScenarioResponse.parse_spending_phases(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["start_age"] == 65

    def test_response_handles_none(self):
        parsed = RetirementScenarioResponse.parse_spending_phases(None)
        assert parsed is None

    def test_response_passes_through_list(self):
        phases = [{"start_age": 65, "end_age": None, "annual_amount": 80000}]
        parsed = RetirementScenarioResponse.parse_spending_phases(phases)
        assert parsed == phases

    def test_spending_phases_field_exists(self):
        assert "spending_phases" in RetirementScenarioResponse.model_fields


# ---------------------------------------------------------------------------
# Spending schedule construction (mirrors simulation logic)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSpendingScheduleConstruction:
    """Test the spending schedule built from phases."""

    @staticmethod
    def _build_schedule(
        phases_json: str | None, annual_spending: float, life_expectancy: int
    ) -> dict[int, float] | None:
        """Replicate the schedule-building logic from monte_carlo_service."""
        import json

        if not phases_json:
            return None
        phases = json.loads(phases_json) if isinstance(phases_json, str) else phases_json
        schedule: dict[int, float] = {}
        for phase in phases:
            end = phase.get("end_age") or life_expectancy
            amount = float(phase["annual_amount"])
            for a in range(phase["start_age"], end + 1):
                schedule[a] = amount
        return schedule

    def test_two_phases(self):
        import json

        phases = json.dumps(
            [
                {"start_age": 65, "end_age": 75, "annual_amount": 150000},
                {"start_age": 75, "end_age": None, "annual_amount": 50000},
            ]
        )
        schedule = self._build_schedule(phases, 60000, 95)
        assert schedule is not None
        assert schedule[65] == 150000
        assert schedule[74] == 150000
        assert schedule[75] == 50000  # Phase boundary: 75 covered by both, last wins
        assert schedule[90] == 50000

    def test_null_phases_returns_none(self):
        schedule = self._build_schedule(None, 60000, 95)
        assert schedule is None

    def test_single_phase_null_end(self):
        import json

        phases = json.dumps(
            [
                {"start_age": 65, "end_age": None, "annual_amount": 80000},
            ]
        )
        schedule = self._build_schedule(phases, 60000, 95)
        assert schedule[65] == 80000
        assert schedule[95] == 80000

    def test_fallback_for_uncovered_ages(self):
        """Ages not covered by phases should fallback to annual_spending."""
        import json

        phases = json.dumps(
            [
                {"start_age": 70, "end_age": None, "annual_amount": 50000},
            ]
        )
        schedule = self._build_schedule(phases, 60000, 95)
        # Age 65 not in schedule — simulation falls back to annual_spending
        assert 65 not in schedule
        assert schedule[70] == 50000


# ---------------------------------------------------------------------------
# Weighted average spending for readiness score
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWeightedAverageSpending:
    """Test the weighted average spending calculation for readiness."""

    @staticmethod
    def _compute_readiness_spending(
        spending_schedule: dict[int, float] | None,
        annual_spending: float,
        retirement_age: int,
        life_expectancy: int,
    ) -> float:
        """Replicate the readiness spending logic from monte_carlo_service."""
        if not spending_schedule:
            return annual_spending
        values = [
            spending_schedule.get(a, annual_spending)
            for a in range(retirement_age, life_expectancy + 1)
        ]
        return sum(values) / len(values) if values else annual_spending

    def test_flat_spending_without_phases(self):
        result = self._compute_readiness_spending(None, 60000, 65, 95)
        assert result == 60000

    def test_weighted_average_two_phases(self):
        schedule = {}
        for a in range(65, 76):
            schedule[a] = 150000
        for a in range(76, 96):
            schedule[a] = 50000
        result = self._compute_readiness_spending(schedule, 60000, 65, 95)
        # 11 years at 150k + 20 years at 50k = 2,650,000 / 31 ≈ 85,483.87
        expected = (11 * 150000 + 20 * 50000) / 31
        assert abs(result - expected) < 1

    def test_partial_coverage_uses_flat_fallback(self):
        """Ages not in schedule fall back to annual_spending."""
        schedule = {a: 100000 for a in range(70, 96)}
        result = self._compute_readiness_spending(schedule, 60000, 65, 95)
        # Ages 65-69 use 60k fallback, 70-95 use 100k
        expected = (5 * 60000 + 26 * 100000) / 31
        assert abs(result - expected) < 1


# ---------------------------------------------------------------------------
# NULLABLE_FIELDS includes spending_phases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNullableFieldsIncludesSpendingPhases:
    """Verify that update_scenario allows clearing spending_phases."""

    @staticmethod
    def _apply_updates(current: dict, updates: dict) -> dict:
        """Replicate the update_scenario setattr logic."""
        NULLABLE_FIELDS = {
            "household_member_ids",
            "household_member_hash",
            "spending_phases",
        }
        result = dict(current)
        for key, value in updates.items():
            if key not in result:
                continue
            if value is None and not key.endswith("_override") and key not in NULLABLE_FIELDS:
                continue
            result[key] = value
        return result

    def test_clears_spending_phases_with_none(self):
        current = {"spending_phases": '[{"start_age":65}]'}
        updates = {"spending_phases": None}
        result = self._apply_updates(current, updates)
        assert result["spending_phases"] is None

    def test_sets_spending_phases_to_new_value(self):
        current = {"spending_phases": None}
        updates = {"spending_phases": '[{"start_age":65}]'}
        result = self._apply_updates(current, updates)
        assert result["spending_phases"] == '[{"start_age":65}]'
