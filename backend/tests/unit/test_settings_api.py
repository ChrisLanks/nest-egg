"""Unit tests for settings API endpoints.

Covers organization preferences GET/PATCH — the API backing the
Organization Preferences section that was moved from PreferencesPage
to HouseholdSettingsPage.

Key behaviours verified:
- Any authenticated user can GET org preferences.
- Only org admins can PATCH org preferences (403 otherwise).
- monthly_start_day is constrained to 1-28 by the schema.
- A missing organization returns 404.
- Only provided fields are updated (partial PATCH).
"""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.settings import (
    get_organization_preferences,
    update_organization_preferences,
    OrganizationPreferencesResponse,
)
from app.schemas.user import OrganizationUpdate
from app.models.user import User, Organization


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(*, is_org_admin: bool = True) -> Mock:
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.is_org_admin = is_org_admin
    return user


def _make_org(*, monthly_start_day: int = 1) -> Mock:
    org = Mock(spec=Organization)
    org.id = uuid4()
    org.name = "Test Org"
    org.monthly_start_day = monthly_start_day
    org.custom_month_end_day = 28
    org.timezone = "UTC"
    return org


def _db_returning(obj):
    """Return a mock DB whose execute() scalar_one_or_none returns obj."""
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = obj
    db.execute.return_value = result
    return db


# ---------------------------------------------------------------------------
# GET /settings/organization
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetOrganizationPreferences:
    """GET /settings/organization — accessible to any authenticated user."""

    @pytest.mark.asyncio
    async def test_returns_org_preferences(self):
        org = _make_org(monthly_start_day=15)
        user = _make_user(is_org_admin=False)  # non-admin can also read
        db = _db_returning(org)

        response = await get_organization_preferences(current_user=user, db=db)

        assert response.monthly_start_day == 15
        assert response.name == "Test Org"
        assert response.timezone == "UTC"

    @pytest.mark.asyncio
    async def test_raises_404_when_org_not_found(self):
        user = _make_user()
        db = _db_returning(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_organization_preferences(current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_non_admin_can_read_preferences(self):
        """Non-admins can read — they just cannot write."""
        org = _make_org()
        user = _make_user(is_org_admin=False)
        db = _db_returning(org)

        response = await get_organization_preferences(current_user=user, db=db)
        assert response is not None


# ---------------------------------------------------------------------------
# PATCH /settings/organization
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUpdateOrganizationPreferences:
    """PATCH /settings/organization — org-admin only."""

    @pytest.mark.asyncio
    async def test_admin_can_update_monthly_start_day(self):
        org = _make_org(monthly_start_day=1)
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        update = OrganizationUpdate(monthly_start_day=16)
        await update_organization_preferences(
            update_data=update, current_user=user, db=db
        )

        assert org.monthly_start_day == 16
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        user = _make_user(is_org_admin=False)
        db = AsyncMock()  # should never be queried

        update = OrganizationUpdate(monthly_start_day=10)
        with pytest.raises(HTTPException) as exc_info:
            await update_organization_preferences(
                update_data=update, current_user=user, db=db
            )

        assert exc_info.value.status_code == 403
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_404_when_org_not_found(self):
        user = _make_user(is_org_admin=True)
        db = _db_returning(None)

        update = OrganizationUpdate(monthly_start_day=5)
        with pytest.raises(HTTPException) as exc_info:
            await update_organization_preferences(
                update_data=update, current_user=user, db=db
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_partial_update_only_touches_provided_fields(self):
        """Omitted fields must not overwrite existing values."""
        org = _make_org(monthly_start_day=10)
        org.name = "Original Name"
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        # Only send monthly_start_day; name not provided
        update = OrganizationUpdate(monthly_start_day=20)
        await update_organization_preferences(
            update_data=update, current_user=user, db=db
        )

        assert org.monthly_start_day == 20
        assert org.name == "Original Name"  # untouched

    @pytest.mark.asyncio
    async def test_start_day_boundary_min(self):
        """Day 1 is the lowest valid value."""
        org = _make_org(monthly_start_day=15)
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        update = OrganizationUpdate(monthly_start_day=1)
        await update_organization_preferences(
            update_data=update, current_user=user, db=db
        )
        assert org.monthly_start_day == 1

    @pytest.mark.asyncio
    async def test_start_day_boundary_max(self):
        """Day 28 is the highest valid value (safe across all months)."""
        org = _make_org(monthly_start_day=1)
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        update = OrganizationUpdate(monthly_start_day=28)
        await update_organization_preferences(
            update_data=update, current_user=user, db=db
        )
        assert org.monthly_start_day == 28


# ---------------------------------------------------------------------------
# Schema validation (OrganizationUpdate)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestOrganizationUpdateSchema:
    """monthly_start_day must be 1-28 (schema-enforced, no DB needed)."""

    def test_rejects_day_zero(self):
        with pytest.raises(Exception):
            OrganizationUpdate(monthly_start_day=0)

    def test_rejects_day_29(self):
        """Day 29 would break on February — schema rejects it."""
        with pytest.raises(Exception):
            OrganizationUpdate(monthly_start_day=29)

    def test_rejects_day_31(self):
        with pytest.raises(Exception):
            OrganizationUpdate(monthly_start_day=31)

    def test_accepts_valid_range(self):
        for day in (1, 15, 28):
            update = OrganizationUpdate(monthly_start_day=day)
            assert update.monthly_start_day == day

    def test_all_fields_optional(self):
        """Empty patch is valid — means no-op update."""
        update = OrganizationUpdate()
        assert update.monthly_start_day is None
        assert update.name is None
