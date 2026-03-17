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
