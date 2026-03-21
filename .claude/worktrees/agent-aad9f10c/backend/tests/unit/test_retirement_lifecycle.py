"""Unit tests for retirement scenario archival lifecycle.

Tests:
- Selective member hash computation
- Schema fields for archival (is_archived, archived_at, archived_reason)
- member_ids on create/update schemas
- Summary includes household_member_ids
- Archival logic (archive on departure, no archive for include_all_members)
- Unarchive validation
- 30-day cleanup logic
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.schemas.retirement import (
    RetirementScenarioCreate,
    RetirementScenarioResponse,
    RetirementScenarioSummary,
    RetirementScenarioUpdate,
)
from app.services.retirement.retirement_planner_service import (
    RetirementPlannerService,
)

# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestArchivalSchemaFields:
    """Test archival-related schema fields."""

    def test_response_has_is_archived(self):
        assert "is_archived" in RetirementScenarioResponse.model_fields
        assert RetirementScenarioResponse.model_fields["is_archived"].default is False

    def test_response_has_archived_at(self):
        assert "archived_at" in RetirementScenarioResponse.model_fields

    def test_response_has_archived_reason(self):
        assert "archived_reason" in RetirementScenarioResponse.model_fields

    def test_summary_has_is_archived(self):
        assert "is_archived" in RetirementScenarioSummary.model_fields
        assert RetirementScenarioSummary.model_fields["is_archived"].default is False

    def test_summary_has_household_member_ids(self):
        assert "household_member_ids" in RetirementScenarioSummary.model_fields

    def test_create_accepts_member_ids(self):
        data = RetirementScenarioCreate(
            name="Multi-user Plan",
            retirement_age=65,
            annual_spending_retirement=60000,
            member_ids=[str(uuid4()), str(uuid4())],
        )
        assert len(data.member_ids) == 2

    def test_create_member_ids_defaults_none(self):
        data = RetirementScenarioCreate(
            name="Solo Plan",
            retirement_age=65,
            annual_spending_retirement=60000,
        )
        assert data.member_ids is None

    def test_update_accepts_member_ids(self):
        ids = [str(uuid4()), str(uuid4())]
        data = RetirementScenarioUpdate(member_ids=ids)
        assert data.member_ids == ids


# ---------------------------------------------------------------------------
# Selective hash tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSelectiveMemberHash:
    """Test compute_selective_member_hash."""

    def test_returns_hash_string(self):
        ids = [str(uuid4()), str(uuid4())]
        h = RetirementPlannerService.compute_selective_member_hash(ids)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_consistent_regardless_of_order(self):
        id1, id2 = str(uuid4()), str(uuid4())
        h1 = RetirementPlannerService.compute_selective_member_hash([id1, id2])
        h2 = RetirementPlannerService.compute_selective_member_hash([id2, id1])
        assert h1 == h2

    def test_different_members_different_hash(self):
        set_a = [str(uuid4()), str(uuid4())]
        set_b = [str(uuid4()), str(uuid4())]
        h1 = RetirementPlannerService.compute_selective_member_hash(set_a)
        h2 = RetirementPlannerService.compute_selective_member_hash(set_b)
        assert h1 != h2

    def test_matches_manual_computation(self):
        ids = [str(uuid4()), str(uuid4())]
        expected = hashlib.sha256(",".join(sorted(ids)).encode()).hexdigest()
        actual = RetirementPlannerService.compute_selective_member_hash(ids)
        assert actual == expected


# ---------------------------------------------------------------------------
# Archive scenarios for departed member
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestArchiveScenariosForDepartedMember:
    """Test archive_scenarios_for_departed_member."""

    @pytest.mark.asyncio
    async def test_archives_selective_scenario_containing_member(self):
        """Selective scenario with departed member should be archived."""
        db = AsyncMock()
        org_id = str(uuid4())
        departed_id = str(uuid4())
        other_id = str(uuid4())

        scenario = Mock()
        scenario.id = uuid4()
        scenario.include_all_members = False
        scenario.is_archived = False
        scenario.household_member_ids = json.dumps([departed_id, other_id])

        result = Mock()
        result.scalars.return_value.all.return_value = [scenario]
        db.execute.return_value = result

        count = await RetirementPlannerService.archive_scenarios_for_departed_member(
            db, org_id, departed_id, departed_user_name="Test User"
        )

        assert count == 1
        assert scenario.is_archived is True
        assert scenario.archived_at is not None
        assert "Test User" in scenario.archived_reason

    @pytest.mark.asyncio
    async def test_skips_include_all_members_scenarios(self):
        """include_all_members=True scenarios should NOT be archived."""
        db = AsyncMock()
        org_id = str(uuid4())
        departed_id = str(uuid4())

        # Return empty list since the query filters for include_all_members=False
        result = Mock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        count = await RetirementPlannerService.archive_scenarios_for_departed_member(
            db, org_id, departed_id, departed_user_name="Test"
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_skips_already_archived(self):
        """Already archived scenarios should not be re-archived."""
        db = AsyncMock()
        org_id = str(uuid4())
        departed_id = str(uuid4())

        # The query filters is_archived=False, so already-archived won't be returned
        result = Mock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        count = await RetirementPlannerService.archive_scenarios_for_departed_member(
            db, org_id, departed_id, departed_user_name="Test"
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_skips_scenario_not_containing_member(self):
        """Scenario without the departed member should not be archived."""
        db = AsyncMock()
        org_id = str(uuid4())
        departed_id = str(uuid4())
        other1, other2 = str(uuid4()), str(uuid4())

        scenario = Mock()
        scenario.id = uuid4()
        scenario.include_all_members = False
        scenario.is_archived = False
        scenario.household_member_ids = json.dumps([other1, other2])

        result = Mock()
        result.scalars.return_value.all.return_value = [scenario]
        db.execute.return_value = result

        count = await RetirementPlannerService.archive_scenarios_for_departed_member(
            db, org_id, departed_id, departed_user_name="Test"
        )

        # Scenario doesn't contain departed_id, should not be archived
        assert scenario.is_archived is False
        assert count == 0


# ---------------------------------------------------------------------------
# Unarchive scenario
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnarchiveScenario:
    """Test unarchive_scenario."""

    @pytest.mark.asyncio
    async def test_unarchive_clears_archive_fields(self):
        """Unarchiving should clear is_archived, archived_at, archived_reason."""
        db = AsyncMock()

        active_id = str(uuid4())
        scenario = Mock()
        scenario.is_archived = True
        scenario.archived_at = datetime.now(timezone.utc)
        scenario.archived_reason = "Member left"
        scenario.household_member_ids = json.dumps([active_id, str(uuid4())])
        scenario.organization_id = uuid4()

        # Mock active user query
        active_result = Mock()
        active_result.scalars.return_value.all.return_value = [active_id]
        db.execute.return_value = active_result

        await RetirementPlannerService.unarchive_scenario(db, scenario)

        assert scenario.is_archived is False
        assert scenario.archived_at is None
        assert scenario.archived_reason is None


# ---------------------------------------------------------------------------
# Cleanup orphaned archived scenarios
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanupOrphanedArchivedScenarios:
    """Test cleanup_orphaned_archived_scenarios."""

    @pytest.mark.asyncio
    async def test_deletes_old_archived_with_no_active_members(self):
        """30+ day old archived scenario with no active members should be deleted."""
        db = AsyncMock()

        scenario = Mock()
        scenario.id = uuid4()
        scenario.is_archived = True
        scenario.archived_at = datetime.now(timezone.utc) - timedelta(days=31)
        scenario.household_member_ids = json.dumps([str(uuid4())])
        scenario.organization_id = uuid4()

        # First call: get candidates, second call: count active members
        candidates_result = Mock()
        candidates_result.scalars.return_value.all.return_value = [scenario]

        active_count_result = Mock()
        active_count_result.scalar.return_value = 0

        db.execute.side_effect = [candidates_result, active_count_result]

        count = await RetirementPlannerService.cleanup_orphaned_archived_scenarios(db)

        assert count == 1
        db.delete.assert_called_once_with(scenario)

    @pytest.mark.asyncio
    async def test_does_not_error_on_empty_list(self):
        """Should handle no archived scenarios gracefully."""
        db = AsyncMock()

        result = Mock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        count = await RetirementPlannerService.cleanup_orphaned_archived_scenarios(db)
        assert count == 0
