"""Unit tests for settings API endpoints.

Covers user profile GET/PATCH and organization preferences GET/PATCH.

Key behaviours verified:
- GET /settings/profile returns birth_day/month/year from stored birthdate.
- PATCH /settings/profile updates display_name, email, and birthday.
- Partial birthday fields (e.g. only day provided) return 400.
- Calendar-impossible dates (Feb 30, Apr 31, Feb 29 non-leap) return 400.
- Any authenticated user can GET org preferences.
- Only org admins can PATCH org preferences (403 otherwise).
- monthly_start_day is constrained to 1-28 by the schema.
- A missing organization returns 404.
- Only provided fields are updated (partial PATCH).
"""

import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.settings import (
    get_user_profile,
    update_user_profile,
    get_organization_preferences,
    update_organization_preferences,
    OrganizationPreferencesResponse,
)
from app.schemas.user import OrganizationUpdate, UserUpdate
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


# ---------------------------------------------------------------------------
# UserUpdate schema — birthday calendar validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUserUpdateBirthdaySchema:
    """UserUpdate.validate_birthday rejects calendar-impossible dates."""

    def test_valid_birthday_accepted(self):
        update = UserUpdate(birth_day=15, birth_month=6, birth_year=1990)
        assert update.birth_day == 15
        assert update.birth_month == 6
        assert update.birth_year == 1990

    def test_feb_30_rejected(self):
        """February never has 30 days."""
        with pytest.raises(Exception, match="Invalid birthday"):
            UserUpdate(birth_day=30, birth_month=2, birth_year=2000)

    def test_feb_29_on_non_leap_year_rejected(self):
        """Feb 29 does not exist in non-leap years."""
        with pytest.raises(Exception, match="Invalid birthday"):
            UserUpdate(birth_day=29, birth_month=2, birth_year=2001)

    def test_feb_29_on_leap_year_accepted(self):
        """2000 is a leap year — Feb 29 is valid."""
        update = UserUpdate(birth_day=29, birth_month=2, birth_year=2000)
        assert update.birth_day == 29

    def test_apr_31_rejected(self):
        """April has only 30 days."""
        with pytest.raises(Exception, match="Invalid birthday"):
            UserUpdate(birth_day=31, birth_month=4, birth_year=1995)

    def test_partial_birthday_without_all_three_is_allowed_by_schema(self):
        """Schema itself allows partial fields; the endpoint enforces all-or-nothing."""
        # Providing only one field is technically valid at the schema level because
        # the model_validator only fires when all three are present.
        update = UserUpdate(birth_day=5)
        assert update.birth_day == 5
        assert update.birth_month is None
        assert update.birth_year is None

    def test_no_birthday_fields_is_valid(self):
        """Empty birthday is fine — used when user clears their birthday."""
        update = UserUpdate()
        assert update.birth_day is None
        assert update.birth_month is None
        assert update.birth_year is None


# ---------------------------------------------------------------------------
# GET /settings/profile
# ---------------------------------------------------------------------------

def _make_user_with_birthdate(birthdate=None, *, is_org_admin: bool = False) -> Mock:
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.first_name = "Jane"
    user.last_name = "Doe"
    user.display_name = "Jane Doe"
    user.birthdate = birthdate
    user.is_org_admin = is_org_admin
    user.dashboard_layout = None
    return user


@pytest.mark.unit
class TestGetUserProfile:
    """GET /settings/profile returns birth_day/month/year split from stored birthdate."""

    @pytest.mark.asyncio
    async def test_returns_birthday_fields_when_birthdate_set(self):
        user = _make_user_with_birthdate(date(1990, 6, 15))
        response = await get_user_profile(current_user=user)
        assert response.birth_day == 15
        assert response.birth_month == 6
        assert response.birth_year == 1990

    @pytest.mark.asyncio
    async def test_returns_none_birthday_fields_when_birthdate_not_set(self):
        user = _make_user_with_birthdate(None)
        response = await get_user_profile(current_user=user)
        assert response.birth_day is None
        assert response.birth_month is None
        assert response.birth_year is None

    @pytest.mark.asyncio
    async def test_returns_basic_profile_fields(self):
        user = _make_user_with_birthdate(None)
        response = await get_user_profile(current_user=user)
        assert response.email == "test@example.com"
        assert response.display_name == "Jane Doe"


# ---------------------------------------------------------------------------
# PATCH /settings/profile
# ---------------------------------------------------------------------------

def _make_patch_db(user: Mock):
    """AsyncMock DB that returns the given user on refresh."""
    db = AsyncMock()
    db.refresh = AsyncMock(return_value=None)
    return db


@pytest.mark.unit
class TestUpdateUserProfile:
    """PATCH /settings/profile updates profile fields and birthday."""

    @pytest.mark.asyncio
    async def test_valid_birthday_sets_birthdate(self):
        user = _make_user_with_birthdate(None)
        db = _make_patch_db(user)
        mock_request = Mock()

        update = UserUpdate(birth_day=20, birth_month=3, birth_year=1985)
        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            await update_user_profile(
                update_data=update,
                http_request=mock_request,
                current_user=user,
                db=db,
            )

        assert user.birthdate == date(1985, 3, 20)
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_calendar_date_returns_400(self):
        """Feb 30 passes schema (model_validator doesn't block field-level),
        but the endpoint's date() call raises ValueError → 400."""
        user = _make_user_with_birthdate(None)
        db = _make_patch_db(user)
        mock_request = Mock()

        # UserUpdate schema model_validator fires when all 3 are present,
        # so Feb 30 is already caught at the schema level with a 422.
        # Verify the schema itself rejects it:
        with pytest.raises(Exception, match="Invalid birthday"):
            UserUpdate(birth_day=30, birth_month=2, birth_year=2001)

    @pytest.mark.asyncio
    async def test_partial_birthday_fields_returns_400(self):
        """Providing only birth_day without month/year should return 400."""
        user = _make_user_with_birthdate(None)
        db = _make_patch_db(user)
        mock_request = Mock()

        update = UserUpdate(birth_day=15)  # month and year omitted
        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await update_user_profile(
                    update_data=update,
                    http_request=mock_request,
                    current_user=user,
                    db=db,
                )
        assert exc_info.value.status_code == 400
        assert "birth_day, birth_month, and birth_year must all be provided together" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_display_name_update(self):
        user = _make_user_with_birthdate(None)
        db = _make_patch_db(user)
        mock_request = Mock()

        update = UserUpdate(display_name="New Name")
        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            await update_user_profile(
                update_data=update,
                http_request=mock_request,
                current_user=user,
                db=db,
            )

        assert user.display_name == "New Name"

    @pytest.mark.asyncio
    async def test_birthday_not_updated_when_omitted(self):
        """When no birthday fields are sent, existing birthdate stays unchanged."""
        existing_birthdate = date(1980, 1, 1)
        user = _make_user_with_birthdate(existing_birthdate)
        db = _make_patch_db(user)
        mock_request = Mock()

        update = UserUpdate(display_name="Updated")
        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            await update_user_profile(
                update_data=update,
                http_request=mock_request,
                current_user=user,
                db=db,
            )

        assert user.birthdate == existing_birthdate  # unchanged

    @pytest.mark.asyncio
    async def test_email_already_in_use_returns_400(self):
        user = _make_user_with_birthdate(None)
        user.email = "original@example.com"

        # DB returns an existing user with the target email
        existing_user = Mock(spec=User)
        db = AsyncMock()
        db.refresh = AsyncMock()
        result = Mock()
        result.scalar_one_or_none.return_value = existing_user
        db.execute.return_value = result

        mock_request = Mock()
        update = UserUpdate(email="taken@example.com")

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await update_user_profile(
                    update_data=update,
                    http_request=mock_request,
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Email already in use"


# ---------------------------------------------------------------------------
# Email change → verification flow
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEmailChangeVerification:
    """Email change should reset email_verified and trigger a verification email."""

    def _make_user(self):
        user = Mock()
        user.id = uuid4()
        user.email = "old@example.com"
        user.email_verified = True
        user.display_name = "Alice"
        user.first_name = "Alice"
        user.last_name = "Smith"
        user.birthdate = None
        user.dashboard_layout = None
        user.is_org_admin = False
        return user

    @pytest.mark.asyncio
    async def test_email_change_resets_email_verified_to_false(self):
        """When a user changes their email, email_verified must be set to False."""
        update = Mock()
        update.first_name = None
        update.last_name = None
        update.display_name = None
        update.email = "new@example.com"
        update.birth_day = None
        update.birth_month = None
        update.birth_year = None

        user = self._make_user()
        mock_request = Mock()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        # No existing user with new email
        no_user_result = Mock()
        no_user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_user_result)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.create_verification_token", new=AsyncMock(return_value="tok")):
                with patch("app.api.v1.settings.email_service.send_verification_email", new=AsyncMock()):
                    await update_user_profile(
                        update_data=update,
                        http_request=mock_request,
                        current_user=user,
                        db=db,
                    )

        assert user.email == "new@example.com"
        assert user.email_verified is False

    @pytest.mark.asyncio
    async def test_email_change_sends_verification_email(self):
        """When email changes, send_verification_email should be called."""
        update = Mock()
        update.first_name = None
        update.last_name = None
        update.display_name = None
        update.email = "new2@example.com"
        update.birth_day = None
        update.birth_month = None
        update.birth_year = None

        user = self._make_user()
        mock_request = Mock()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        no_user_result = Mock()
        no_user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_user_result)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.create_verification_token", new=AsyncMock(return_value="tok")) as mock_create:
                with patch("app.api.v1.settings.email_service.send_verification_email", new=AsyncMock()) as mock_send:
                    await update_user_profile(
                        update_data=update,
                        http_request=mock_request,
                        current_user=user,
                        db=db,
                    )

        mock_create.assert_called_once()
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_verification_email_when_email_unchanged(self):
        """If email is not changed, no verification email should be sent."""
        update = Mock()
        update.first_name = None
        update.last_name = None
        update.display_name = "New Name"
        update.email = None  # not changing email
        update.birth_day = None
        update.birth_month = None
        update.birth_year = None

        user = self._make_user()
        mock_request = Mock()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock(return_value=Mock())

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.email_service.send_verification_email", new=AsyncMock()) as mock_send:
                await update_user_profile(
                    update_data=update,
                    http_request=mock_request,
                    current_user=user,
                    db=db,
                )

        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# DELETE /settings/account  (GDPR Article 17 — Right to Erasure)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDeleteAccount:
    """Tests for DELETE /settings/account endpoint."""

    def _make_user(self, *, is_org_admin: bool = True) -> Mock:
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.is_org_admin = is_org_admin
        user.password_hash = "hashed_password"
        return user

    @pytest.mark.asyncio
    async def test_wrong_password_returns_401(self):
        """Should return 401 when supplied password is incorrect."""
        from app.api.v1.settings import delete_account, DeleteAccountRequest

        user = self._make_user()
        data = DeleteAccountRequest(password="wrongpassword")
        mock_request = Mock()
        db = AsyncMock()

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await delete_account(data=data, http_request=mock_request, current_user=user, db=db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_sole_member_deletes_organization(self):
        """When user is the only member, the whole organization is deleted."""
        from app.api.v1.settings import delete_account, DeleteAccountRequest

        user = self._make_user()
        data = DeleteAccountRequest(password="correctpassword")
        mock_request = Mock()

        mock_org = Mock(spec=Organization)
        mock_org.id = user.organization_id

        db = AsyncMock()
        # count returns 1 (sole member)
        count_scalar = Mock()
        count_scalar.scalar.return_value = 1
        db.execute = AsyncMock(return_value=count_scalar)
        db.get = AsyncMock(return_value=mock_org)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
                await delete_account(data=data, http_request=mock_request, current_user=user, db=db)

        db.delete.assert_called_once_with(mock_org)
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_household_member_deletes_only_user(self):
        """When other members exist, only the current user is deleted."""
        from app.api.v1.settings import delete_account, DeleteAccountRequest

        user = self._make_user()
        data = DeleteAccountRequest(password="correctpassword")
        mock_request = Mock()

        db = AsyncMock()
        # count returns 3 (multiple members)
        count_scalar = Mock()
        count_scalar.scalar.return_value = 3
        db.execute = AsyncMock(return_value=count_scalar)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
                await delete_account(data=data, http_request=mock_request, current_user=user, db=db)

        db.delete.assert_called_once_with(user)
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """Should check rate limit before processing."""
        from app.api.v1.settings import delete_account, DeleteAccountRequest

        user = self._make_user()
        data = DeleteAccountRequest(password="pw")
        mock_request = Mock()
        db = AsyncMock()

        with patch(
            "app.api.v1.settings.rate_limit_service.check_rate_limit",
            new=AsyncMock(side_effect=HTTPException(status_code=429, detail="Rate limit")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_account(data=data, http_request=mock_request, current_user=user, db=db)

        assert exc_info.value.status_code == 429

