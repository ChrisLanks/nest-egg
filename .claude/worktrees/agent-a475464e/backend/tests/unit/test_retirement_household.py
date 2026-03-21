"""Unit tests for retirement household-wide planning features.

Tests:
- compute_household_member_hash consistency and uniqueness
- RetirementScenarioCreate accepts include_all_members
- RetirementScenarioResponse has is_stale field
- RetirementScenarioSummary has is_stale and include_all_members fields
"""

import hashlib
from uuid import uuid4

import pytest

from app.schemas.retirement import (
    RetirementScenarioCreate,
    RetirementScenarioResponse,
    RetirementScenarioSummary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_hash(member_ids: list[str]) -> str:
    """Replicate the hash logic from RetirementPlannerService."""
    sorted_ids = sorted(member_ids)
    return hashlib.sha256(",".join(sorted_ids).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComputeHouseholdMemberHash:
    """Test the member hash computation logic."""

    def test_consistent_hash_for_same_members(self):
        """Same member IDs should always produce the same hash."""
        ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        hash1 = _compute_hash(ids)
        hash2 = _compute_hash(ids)
        assert hash1 == hash2

    def test_consistent_hash_regardless_of_order(self):
        """Member IDs in different order should produce the same hash."""
        id1, id2, id3 = str(uuid4()), str(uuid4()), str(uuid4())
        hash_asc = _compute_hash([id1, id2, id3])
        hash_desc = _compute_hash([id3, id2, id1])
        assert hash_asc == hash_desc

    def test_different_hash_when_members_change(self):
        """Adding or removing a member should change the hash."""
        id1, id2, id3 = str(uuid4()), str(uuid4()), str(uuid4())
        hash_two = _compute_hash([id1, id2])
        hash_three = _compute_hash([id1, id2, id3])
        assert hash_two != hash_three

    def test_different_hash_for_different_members(self):
        """Completely different member sets produce different hashes."""
        set_a = [str(uuid4()), str(uuid4())]
        set_b = [str(uuid4()), str(uuid4())]
        assert _compute_hash(set_a) != _compute_hash(set_b)

    def test_hash_is_sha256_hex(self):
        """Hash should be a 64-character hex string (SHA-256)."""
        ids = [str(uuid4())]
        h = _compute_hash(ids)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_single_member_hash(self):
        """Single member should still produce a valid hash."""
        h = _compute_hash([str(uuid4())])
        assert isinstance(h, str)
        assert len(h) == 64

    def test_empty_member_list(self):
        """Empty member list should produce a deterministic hash."""
        h = _compute_hash([])
        expected = hashlib.sha256("".encode()).hexdigest()
        assert h == expected


@pytest.mark.unit
class TestRetirementScenarioCreateSchema:
    """Test RetirementScenarioCreate schema validation."""

    def test_accepts_include_all_members_true(self):
        """Schema should accept include_all_members=True."""
        data = RetirementScenarioCreate(
            name="Household Plan",
            retirement_age=65,
            annual_spending_retirement=60000,
            include_all_members=True,
        )
        assert data.include_all_members is True

    def test_include_all_members_defaults_to_false(self):
        """Schema should default include_all_members to False."""
        data = RetirementScenarioCreate(
            name="Solo Plan",
            retirement_age=65,
            annual_spending_retirement=60000,
        )
        assert data.include_all_members is False

    def test_accepts_all_required_fields(self):
        """Schema should accept minimal required fields."""
        data = RetirementScenarioCreate(
            name="Test Plan",
            retirement_age=65,
            annual_spending_retirement=60000,
        )
        assert data.name == "Test Plan"
        assert data.retirement_age == 65


@pytest.mark.unit
class TestRetirementScenarioResponseSchema:
    """Test RetirementScenarioResponse schema fields."""

    def test_is_stale_field_exists_and_defaults_false(self):
        """Response schema should have is_stale field defaulting to False."""
        # Verify the field exists by checking model_fields
        assert "is_stale" in RetirementScenarioResponse.model_fields
        assert RetirementScenarioResponse.model_fields["is_stale"].default is False

    def test_include_all_members_field_exists(self):
        """Response schema should have include_all_members field."""
        assert "include_all_members" in RetirementScenarioResponse.model_fields

    def test_household_member_ids_field_exists(self):
        """Response schema should have household_member_ids field."""
        assert "household_member_ids" in RetirementScenarioResponse.model_fields


@pytest.mark.unit
class TestRetirementScenarioSummarySchema:
    """Test RetirementScenarioSummary schema fields."""

    def test_is_stale_field_defaults_false(self):
        """Summary schema should have is_stale defaulting to False."""
        assert "is_stale" in RetirementScenarioSummary.model_fields
        assert RetirementScenarioSummary.model_fields["is_stale"].default is False

    def test_include_all_members_field_defaults_false(self):
        """Summary schema should have include_all_members defaulting to False."""
        assert "include_all_members" in RetirementScenarioSummary.model_fields
        assert RetirementScenarioSummary.model_fields["include_all_members"].default is False

    def test_user_id_field_exists(self):
        """Summary schema should have user_id field for view filtering."""
        assert "user_id" in RetirementScenarioSummary.model_fields


@pytest.mark.unit
class TestRetirementScenarioUpdateSchema:
    """Test RetirementScenarioUpdate schema for member editing."""

    def test_member_ids_field_exists(self):
        """Update schema should have member_ids field."""
        from app.schemas.retirement import RetirementScenarioUpdate

        assert "member_ids" in RetirementScenarioUpdate.model_fields

    def test_include_all_members_field_exists(self):
        """Update schema should have include_all_members field."""
        from app.schemas.retirement import RetirementScenarioUpdate

        assert "include_all_members" in RetirementScenarioUpdate.model_fields

    def test_member_ids_accepts_list(self):
        """Update schema should accept a list of member IDs."""
        from app.schemas.retirement import RetirementScenarioUpdate

        data = RetirementScenarioUpdate(member_ids=["u1", "u2", "u3"])
        assert data.member_ids == ["u1", "u2", "u3"]

    def test_member_ids_accepts_empty_list(self):
        """Update schema should accept an empty list (revert to personal)."""
        from app.schemas.retirement import RetirementScenarioUpdate

        data = RetirementScenarioUpdate(member_ids=[])
        assert data.member_ids == []

    def test_member_ids_defaults_to_none(self):
        """Update schema should default member_ids to None (unset)."""
        from app.schemas.retirement import RetirementScenarioUpdate

        data = RetirementScenarioUpdate(name="Renamed")
        assert data.member_ids is None

    def test_exclude_unset_omits_member_ids_when_not_provided(self):
        """model_dump(exclude_unset=True) should not include member_ids if not set."""
        from app.schemas.retirement import RetirementScenarioUpdate

        data = RetirementScenarioUpdate(name="Renamed")
        dumped = data.model_dump(exclude_unset=True)
        assert "member_ids" not in dumped

    def test_exclude_unset_includes_member_ids_when_provided(self):
        """model_dump(exclude_unset=True) should include member_ids when explicitly set."""
        from app.schemas.retirement import RetirementScenarioUpdate

        data = RetirementScenarioUpdate(member_ids=["u1", "u2"])
        dumped = data.model_dump(exclude_unset=True)
        assert "member_ids" in dumped
        assert dumped["member_ids"] == ["u1", "u2"]

    def test_exclude_unset_includes_empty_member_ids(self):
        """model_dump(exclude_unset=True) should include member_ids=[] when explicitly set."""
        from app.schemas.retirement import RetirementScenarioUpdate

        data = RetirementScenarioUpdate(member_ids=[])
        dumped = data.model_dump(exclude_unset=True)
        assert "member_ids" in dumped
        assert dumped["member_ids"] == []


@pytest.mark.unit
class TestMemberIdsUpdateProcessing:
    """Test the API-level member_ids → household_member_ids processing logic.

    Mirrors the transform in PATCH /scenarios/{id} without needing a running server.
    """

    @staticmethod
    def _process_member_ids(updates: dict) -> dict:
        """Replicate the member_ids processing from the PATCH endpoint."""
        import json

        new_member_ids = updates.pop("member_ids", None)
        if new_member_ids is not None:
            if len(new_member_ids) >= 2:
                sorted_ids = sorted(new_member_ids)
                updates["household_member_ids"] = json.dumps(sorted_ids)
                updates["household_member_hash"] = _compute_hash(sorted_ids)
                updates["include_all_members"] = False
            else:
                updates["household_member_ids"] = None
                updates["household_member_hash"] = None
                updates["include_all_members"] = False

        if new_member_ids is None and updates.get("include_all_members") is True:
            updates["household_member_ids"] = None
            updates["household_member_hash"] = None

        return updates

    def test_two_members_sets_json_and_hash(self):
        """2+ member_ids should produce JSON household_member_ids and a hash."""
        import json

        updates = {"member_ids": ["u2", "u1"]}
        result = self._process_member_ids(updates)
        assert "member_ids" not in result  # popped
        assert json.loads(result["household_member_ids"]) == ["u1", "u2"]  # sorted
        assert result["household_member_hash"] == _compute_hash(["u1", "u2"])
        assert result["include_all_members"] is False

    def test_three_members_sorted(self):
        """3 member_ids should be sorted in the JSON."""
        import json

        updates = {"member_ids": ["u3", "u1", "u2"]}
        result = self._process_member_ids(updates)
        assert json.loads(result["household_member_ids"]) == ["u1", "u2", "u3"]

    def test_empty_member_ids_clears_household_fields(self):
        """Empty member_ids should clear household_member_ids and hash."""
        updates = {"member_ids": []}
        result = self._process_member_ids(updates)
        assert result["household_member_ids"] is None
        assert result["household_member_hash"] is None
        assert result["include_all_members"] is False

    def test_single_member_id_clears_household_fields(self):
        """Single member_id should clear household fields (personal plan)."""
        updates = {"member_ids": ["u1"]}
        result = self._process_member_ids(updates)
        assert result["household_member_ids"] is None
        assert result["household_member_hash"] is None
        assert result["include_all_members"] is False

    def test_include_all_members_without_member_ids_clears_fields(self):
        """Setting include_all_members=True without member_ids should clear stored members."""
        updates = {"include_all_members": True}
        result = self._process_member_ids(updates)
        assert result["household_member_ids"] is None
        assert result["household_member_hash"] is None
        assert result["include_all_members"] is True

    def test_no_member_ids_no_include_all_passes_through(self):
        """Updates without member_ids or include_all_members should pass through unchanged."""
        updates = {"name": "Renamed", "retirement_age": 70}
        result = self._process_member_ids(updates)
        assert result == {"name": "Renamed", "retirement_age": 70}

    def test_member_ids_not_in_final_updates(self):
        """member_ids should always be popped from the final updates dict."""
        updates = {"member_ids": ["u1", "u2"], "name": "Joint"}
        result = self._process_member_ids(updates)
        assert "member_ids" not in result
        assert "name" in result


@pytest.mark.unit
class TestUpdateScenarioNullableFields:
    """Test that update_scenario allows clearing household fields with None.

    Mirrors the service logic without needing a DB session.
    """

    @staticmethod
    def _apply_updates(current: dict, updates: dict) -> dict:
        """Replicate the update_scenario setattr logic."""
        NULLABLE_FIELDS = {"household_member_ids", "household_member_hash"}
        result = dict(current)
        for key, value in updates.items():
            if key not in result:
                continue
            if value is None and not key.endswith("_override") and key not in NULLABLE_FIELDS:
                continue
            result[key] = value
        return result

    def test_clears_household_member_ids_with_none(self):
        """Setting household_member_ids=None should clear the field."""
        current = {
            "household_member_ids": '["u1","u2"]',
            "household_member_hash": "abc123",
            "include_all_members": False,
        }
        updates = {
            "household_member_ids": None,
            "household_member_hash": None,
            "include_all_members": False,
        }
        result = self._apply_updates(current, updates)
        assert result["household_member_ids"] is None
        assert result["household_member_hash"] is None
        assert result["include_all_members"] is False

    def test_preserves_non_nullable_fields_when_none(self):
        """Setting a non-nullable, non-override field to None should be skipped."""
        current = {"name": "My Plan", "retirement_age": 65}
        updates = {"name": None, "retirement_age": None}
        result = self._apply_updates(current, updates)
        assert result["name"] == "My Plan"
        assert result["retirement_age"] == 65

    def test_allows_override_fields_to_be_none(self):
        """Fields ending in _override should accept None."""
        current = {"healthcare_pre65_override": 500}
        updates = {"healthcare_pre65_override": None}
        result = self._apply_updates(current, updates)
        assert result["healthcare_pre65_override"] is None

    def test_updates_household_member_ids_to_new_value(self):
        """Setting household_member_ids to a new JSON value should work."""
        current = {
            "household_member_ids": '["u1","u2"]',
            "household_member_hash": "old",
        }
        updates = {
            "household_member_ids": '["u1","u2","u3"]',
            "household_member_hash": "new",
        }
        result = self._apply_updates(current, updates)
        assert result["household_member_ids"] == '["u1","u2","u3"]'
        assert result["household_member_hash"] == "new"

    def test_skips_unknown_fields(self):
        """Unknown fields not present in current should be ignored."""
        current = {"name": "My Plan"}
        updates = {"nonexistent_field": "value"}
        result = self._apply_updates(current, updates)
        assert "nonexistent_field" not in result
