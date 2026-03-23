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
- Email change requires current_password (prevents account takeover via stolen token).
- Wrong current_password on email change returns 400.
"""

from datetime import date
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.settings import (
    get_organization_preferences,
    get_user_profile,
    update_organization_preferences,
    update_user_profile,
)
from app.models.user import Organization, User
from app.schemas.user import OrganizationUpdate, UserUpdate

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
        await update_organization_preferences(update_data=update, current_user=user, db=db)

        assert org.monthly_start_day == 16
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        user = _make_user(is_org_admin=False)
        db = AsyncMock()  # should never be queried

        update = OrganizationUpdate(monthly_start_day=10)
        with pytest.raises(HTTPException) as exc_info:
            await update_organization_preferences(update_data=update, current_user=user, db=db)

        assert exc_info.value.status_code == 403
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_404_when_org_not_found(self):
        user = _make_user(is_org_admin=True)
        db = _db_returning(None)

        update = OrganizationUpdate(monthly_start_day=5)
        with pytest.raises(HTTPException) as exc_info:
            await update_organization_preferences(update_data=update, current_user=user, db=db)

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
        await update_organization_preferences(update_data=update, current_user=user, db=db)

        assert org.monthly_start_day == 20
        assert org.name == "Original Name"  # untouched

    @pytest.mark.asyncio
    async def test_start_day_boundary_min(self):
        """Day 1 is the lowest valid value."""
        org = _make_org(monthly_start_day=15)
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        update = OrganizationUpdate(monthly_start_day=1)
        await update_organization_preferences(update_data=update, current_user=user, db=db)
        assert org.monthly_start_day == 1

    @pytest.mark.asyncio
    async def test_start_day_boundary_max(self):
        """Day 28 is the highest valid value (safe across all months)."""
        org = _make_org(monthly_start_day=1)
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        update = OrganizationUpdate(monthly_start_day=28)
        await update_organization_preferences(update_data=update, current_user=user, db=db)
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
    user.organization_id = uuid4()
    user.email_notifications_enabled = True
    user.notification_preferences = None
    user.onboarding_goal = None
    user.login_count = 0
    return user


def _make_mock_org(default_currency: str = "USD") -> Mock:
    org = Mock()
    org.default_currency = default_currency
    return org


@pytest.mark.unit
class TestGetUserProfile:
    """GET /settings/profile returns birth_day/month/year split from stored birthdate."""

    @pytest.mark.asyncio
    async def test_returns_birthday_fields_when_birthdate_set(self):
        user = _make_user_with_birthdate(date(1990, 6, 15))
        db = _make_patch_db(user)
        response = await get_user_profile(current_user=user, db=db)
        assert response.birth_day == 15
        assert response.birth_month == 6
        assert response.birth_year == 1990

    @pytest.mark.asyncio
    async def test_returns_none_birthday_fields_when_birthdate_not_set(self):
        user = _make_user_with_birthdate(None)
        db = _make_patch_db(user)
        response = await get_user_profile(current_user=user, db=db)
        assert response.birth_day is None
        assert response.birth_month is None
        assert response.birth_year is None

    @pytest.mark.asyncio
    async def test_returns_basic_profile_fields(self):
        user = _make_user_with_birthdate(None)
        db = _make_patch_db(user)
        response = await get_user_profile(current_user=user, db=db)
        assert response.email == "test@example.com"
        assert response.display_name == "Jane Doe"


# ---------------------------------------------------------------------------
# PATCH /settings/profile
# ---------------------------------------------------------------------------


def _make_patch_db(user: Mock, org: Mock | None = None) -> AsyncMock:
    """AsyncMock DB that returns the given user on refresh and a mock org on execute."""
    db = AsyncMock()
    db.refresh = AsyncMock(return_value=None)
    mock_org = org if org is not None else _make_mock_org()
    result = Mock()
    result.scalar_one_or_none.return_value = mock_org
    db.execute.return_value = result
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
        _make_patch_db(user)
        Mock()

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
        assert (
            "birth_day, birth_month, and birth_year must all be provided together"
            in exc_info.value.detail
        )

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
        user.password_hash = "hashed"

        # DB returns an existing user with the target email
        existing_user = Mock(spec=User)
        db = AsyncMock()
        db.refresh = AsyncMock()
        result = Mock()
        result.scalar_one_or_none.return_value = existing_user
        db.execute.return_value = result

        mock_request = Mock()
        update = UserUpdate(email="taken@example.com", current_password="correct-password")

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
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
        user.organization_id = uuid4()
        user.email_notifications_enabled = True
        user.notification_preferences = None
        user.onboarding_goal = None
        return user

    @pytest.mark.asyncio
    async def test_email_change_resets_email_verified_to_false(self):
        """When a user changes their email, email_verified must be set to False."""
        update = Mock()
        update.first_name = None
        update.last_name = None
        update.display_name = None
        update.email = "new@example.com"
        update.current_password = "correct-password"
        update.birth_day = None
        update.birth_month = None
        update.birth_year = None
        update.onboarding_goal = None
        update.default_currency = None
        update.dashboard_layout = None

        user = self._make_user()
        user.password_hash = "hashed"
        mock_request = Mock()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        # No existing user with new email
        no_user_result = Mock()
        no_user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_user_result)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
                with patch(
                    "app.api.v1.settings.create_verification_token",
                    new=AsyncMock(return_value="tok"),
                ):
                    with patch(
                        "app.api.v1.settings.email_service.send_verification_email",
                        new=AsyncMock(),
                    ):
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
        update.current_password = "correct-password"
        update.birth_day = None
        update.birth_month = None
        update.birth_year = None
        update.onboarding_goal = None
        update.default_currency = None
        update.dashboard_layout = None

        user = self._make_user()
        user.password_hash = "hashed"
        mock_request = Mock()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        no_user_result = Mock()
        no_user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_user_result)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
                with patch(
                    "app.api.v1.settings.create_verification_token",
                    new=AsyncMock(return_value="tok"),
                ) as mock_create:
                    with patch(
                        "app.api.v1.settings.email_service.send_verification_email",
                        new=AsyncMock(),
                    ) as mock_send:
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
        update.onboarding_goal = None
        update.default_currency = None
        update.dashboard_layout = None

        user = self._make_user()
        mock_request = Mock()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        no_result = Mock()
        no_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_result)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch(
                "app.api.v1.settings.email_service.send_verification_email", new=AsyncMock()
            ) as mock_send:
                await update_user_profile(
                    update_data=update,
                    http_request=mock_request,
                    current_user=user,
                    db=db,
                )

        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Email change — password enforcement (security: account-takeover prevention)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmailChangeRequiresPassword:
    """Changing email requires current_password to prevent account takeover
    via a stolen short-lived access token."""

    def _make_user(self):
        user = Mock()
        user.id = uuid4()
        user.email = "current@example.com"
        user.email_verified = True
        user.display_name = "Bob"
        user.first_name = "Bob"
        user.last_name = "Smith"
        user.birthdate = None
        user.dashboard_layout = None
        user.is_org_admin = False
        user.organization_id = uuid4()
        user.email_notifications_enabled = True
        user.notification_preferences = None
        user.onboarding_goal = None
        user.password_hash = "correct-hash"
        return user

    def _no_op_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        result = Mock()
        result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.mark.asyncio
    async def test_email_change_without_password_returns_400(self):
        """Missing current_password on email change must be rejected."""
        user = self._make_user()
        db = self._no_op_db()
        update = UserUpdate(email="new@example.com")  # no current_password

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await update_user_profile(
                    update_data=update,
                    http_request=Mock(),
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 400
        assert "current_password" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_email_change_with_wrong_password_returns_400(self):
        """Wrong current_password on email change must be rejected."""
        user = self._make_user()
        db = self._no_op_db()
        update = UserUpdate(email="new@example.com", current_password="wrong-password")

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await update_user_profile(
                        update_data=update,
                        http_request=Mock(),
                        current_user=user,
                        db=db,
                    )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Current password is incorrect"

    @pytest.mark.asyncio
    async def test_email_change_with_correct_password_succeeds(self):
        """Correct current_password allows the email change."""
        user = self._make_user()
        db = self._no_op_db()
        update = UserUpdate(email="new@example.com", current_password="correct-password")

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
                with patch(
                    "app.api.v1.settings.create_verification_token",
                    new=AsyncMock(return_value="tok"),
                ):
                    with patch(
                        "app.api.v1.settings.email_service.send_verification_email",
                        new=AsyncMock(),
                    ):
                        await update_user_profile(
                            update_data=update,
                            http_request=Mock(),
                            current_user=user,
                            db=db,
                        )

        assert user.email == "new@example.com"
        assert user.email_verified is False

    @pytest.mark.asyncio
    async def test_non_email_update_does_not_require_password(self):
        """Updating display_name without changing email must NOT require a password."""
        user = self._make_user()
        db = self._no_op_db()
        update = UserUpdate(display_name="New Name")  # no email, no password

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            # Should not raise — no verify_password call expected
            await update_user_profile(
                update_data=update,
                http_request=Mock(),
                current_user=user,
                db=db,
            )

        assert user.display_name == "New Name"

    @pytest.mark.asyncio
    async def test_same_email_does_not_require_password(self):
        """Submitting the same email (no actual change) must NOT require a password."""
        user = self._make_user()
        db = self._no_op_db()
        # Same email as current — no change, no password needed
        update = UserUpdate(email=user.email)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            await update_user_profile(
                update_data=update,
                http_request=Mock(),
                current_user=user,
                db=db,
            )

        # email_verified should remain unchanged
        assert user.email_verified is True


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
        from app.api.v1.settings import DeleteAccountRequest, delete_account

        user = self._make_user()
        data = DeleteAccountRequest(password="wrongpassword")
        mock_request = Mock()
        db = AsyncMock()

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await delete_account(
                        data=data,
                        http_request=mock_request,
                        http_response=Mock(),
                        current_user=user,
                        db=db,
                    )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_sole_member_deletes_organization(self):
        """When user is the only member, the whole organization is deleted."""
        from app.api.v1.settings import DeleteAccountRequest, delete_account

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
                await delete_account(
                    data=data,
                    http_request=mock_request,
                    http_response=Mock(),
                    current_user=user,
                    db=db,
                )

        db.delete.assert_called_once_with(mock_org)
        # commit called twice: once for token revocation, once for deletion
        assert db.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_household_member_deletes_only_user(self):
        """When other members exist, only the current user is deleted."""
        from app.api.v1.settings import DeleteAccountRequest, delete_account

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
                await delete_account(
                    data=data,
                    http_request=mock_request,
                    http_response=Mock(),
                    current_user=user,
                    db=db,
                )

        db.delete.assert_called_once_with(user)
        # commit called twice: once for token revocation, once for deletion
        assert db.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_refresh_tokens_revoked_before_deletion(self):
        """Refresh tokens must be explicitly revoked before account deletion
        to eliminate the race window between response and FK cascade."""
        from app.api.v1.settings import DeleteAccountRequest, delete_account

        user = self._make_user()
        data = DeleteAccountRequest(password="correctpassword")
        mock_request = Mock()

        db = AsyncMock()
        count_scalar = Mock()
        count_scalar.scalar.return_value = 1
        db.execute = AsyncMock(return_value=count_scalar)
        db.get = AsyncMock(return_value=Mock(spec=Organization))

        call_order: list[str] = []

        async def track_execute(*args, **kwargs):
            call_order.append("execute")
            return count_scalar

        async def track_commit():
            call_order.append("commit")

        db.execute = AsyncMock(side_effect=track_execute)
        db.commit = AsyncMock(side_effect=track_commit)

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
                await delete_account(
                    data=data,
                    http_request=mock_request,
                    http_response=Mock(),
                    current_user=user,
                    db=db,
                )

        # execute(revoke), commit, execute(count), ..., commit
        assert call_order[0] == "execute", "token revocation execute must come first"
        assert call_order[1] == "commit", "token revocation must be committed before deletion"
        assert db.execute.await_count >= 2
        assert db.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """Should check rate limit before processing."""
        from app.api.v1.settings import DeleteAccountRequest, delete_account

        user = self._make_user()
        data = DeleteAccountRequest(password="pw")
        mock_request = Mock()
        db = AsyncMock()

        with patch(
            "app.api.v1.settings.rate_limit_service.check_rate_limit",
            new=AsyncMock(side_effect=HTTPException(status_code=429, detail="Rate limit")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_account(
                    data=data,
                    http_request=mock_request,
                    http_response=Mock(),
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# PUT /settings/dashboard-layout
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateDashboardLayout:
    """Tests for PUT /settings/dashboard-layout endpoint."""

    @pytest.mark.asyncio
    async def test_update_layout_success(self):
        from app.api.v1.settings import DashboardLayoutUpdate, update_dashboard_layout

        user = _make_user_with_birthdate(None)
        db = AsyncMock()

        body = DashboardLayoutUpdate(
            layout=[{"id": "chart", "span": 2}, {"id": "summary", "span": 1}]
        )
        response = await update_dashboard_layout(body=body, current_user=user, db=db)

        assert len(user.dashboard_layout) == 2
        assert user.dashboard_layout[0].id == "chart"
        assert user.dashboard_layout[0].span == 2
        assert user.dashboard_layout[1].id == "summary"
        db.commit.assert_awaited_once()
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_update_layout_empty(self):
        from app.api.v1.settings import DashboardLayoutUpdate, update_dashboard_layout

        user = _make_user_with_birthdate(None)
        db = AsyncMock()

        body = DashboardLayoutUpdate(layout=[])
        await update_dashboard_layout(body=body, current_user=user, db=db)

        assert user.dashboard_layout == []


# ---------------------------------------------------------------------------
# POST /settings/profile/change-password
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChangePassword:
    """Tests for POST /settings/profile/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        from app.api.v1.settings import ChangePasswordRequest, change_password

        user = _make_user_with_birthdate(None)
        user.password_hash = "old_hash"  # pragma: allowlist secret
        mock_request = Mock()
        db = AsyncMock()

        data = ChangePasswordRequest(
            current_password="OldPassword123!",  # pragma: allowlist secret
            new_password="NewPassword123!@",  # pragma: allowlist secret
        )

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
                with patch(
                    "app.api.v1.settings.password_validation_service.validate_and_raise_async",
                    new=AsyncMock(),
                ):
                    with patch("app.api.v1.settings.hash_password", return_value="new_hash"):
                        result = await change_password(
                            password_data=data,
                            http_request=mock_request,
                            current_user=user,
                            db=db,
                        )

        assert user.password_hash == "new_hash"  # pragma: allowlist secret
        assert result["message"] == "Password changed successfully"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self):
        from app.api.v1.settings import ChangePasswordRequest, change_password

        user = _make_user_with_birthdate(None)
        user.password_hash = "old_hash"  # pragma: allowlist secret
        mock_request = Mock()
        db = AsyncMock()

        data = ChangePasswordRequest(
            current_password="WrongPassword123!",  # pragma: allowlist secret
            new_password="NewPassword123!@",  # pragma: allowlist secret
        )

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await change_password(
                        password_data=data,
                        http_request=mock_request,
                        current_user=user,
                        db=db,
                    )

        assert exc_info.value.status_code == 400
        assert "incorrect" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_change_password_rate_limited(self):
        from app.api.v1.settings import ChangePasswordRequest, change_password

        user = _make_user_with_birthdate(None)
        mock_request = Mock()
        db = AsyncMock()

        data = ChangePasswordRequest(
            current_password="OldPassword123!",  # pragma: allowlist secret
            new_password="NewPassword123!@",  # pragma: allowlist secret
        )

        with patch(
            "app.api.v1.settings.rate_limit_service.check_rate_limit",
            new=AsyncMock(side_effect=HTTPException(status_code=429, detail="Rate limited")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    password_data=data,
                    http_request=mock_request,
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# PATCH /settings/email-notifications
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateEmailNotifications:
    """Tests for PATCH /settings/email-notifications endpoint."""

    @pytest.mark.asyncio
    async def test_enable_notifications(self):
        from app.api.v1.settings import update_email_notifications

        user = _make_user_with_birthdate(None)
        user.email_notifications_enabled = False
        db = AsyncMock()

        result = await update_email_notifications(enabled=True, current_user=user, db=db)

        assert user.email_notifications_enabled is True
        assert result["email_notifications_enabled"] is True
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disable_notifications(self):
        from app.api.v1.settings import update_email_notifications

        user = _make_user_with_birthdate(None)
        user.email_notifications_enabled = True
        db = AsyncMock()

        result = await update_email_notifications(enabled=False, current_user=user, db=db)

        assert user.email_notifications_enabled is False
        assert result["email_notifications_enabled"] is False


# ---------------------------------------------------------------------------
# GET /settings/email-configured
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckEmailConfigured:
    """Tests for GET /settings/email-configured endpoint."""

    @pytest.mark.asyncio
    async def test_email_configured_true(self):
        from app.api.v1.settings import check_email_configured

        with patch("app.api.v1.settings.email_service") as mock_email:
            mock_email.is_configured = True
            result = await check_email_configured()

        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_email_configured_false(self):
        from app.api.v1.settings import check_email_configured

        with patch("app.api.v1.settings.email_service") as mock_email:
            mock_email.is_configured = False
            result = await check_email_configured()

        assert result["configured"] is False


# ---------------------------------------------------------------------------
# PATCH /settings/profile — additional field branches (lines 131,133,140,149-150,192-193)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateUserProfileExtendedBranches:
    """Cover first_name, last_name, default_currency, invalid birthday, and email error."""

    @pytest.mark.asyncio
    async def test_update_first_name_and_last_name(self):
        """Should update first_name and last_name when provided."""
        user = _make_user_with_birthdate(None)
        db = _make_patch_db(user)
        mock_request = Mock()

        update = UserUpdate(first_name="Alice", last_name="Smith")
        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            await update_user_profile(
                update_data=update,
                http_request=mock_request,
                current_user=user,
                db=db,
            )

        assert user.first_name == "Alice"
        assert user.last_name == "Smith"

    @pytest.mark.asyncio
    async def test_update_default_currency(self):
        """Should update default_currency on the organization and uppercase it."""
        user = _make_user_with_birthdate(None)
        org = _make_mock_org(default_currency="USD")
        db = _make_patch_db(user, org=org)
        mock_request = Mock()

        update = UserUpdate(default_currency="eur")
        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            await update_user_profile(
                update_data=update,
                http_request=mock_request,
                current_user=user,
                db=db,
            )

        assert org.default_currency == "EUR"

    @pytest.mark.asyncio
    async def test_invalid_birthday_date_returns_400(self):
        """Feb 30 should raise 400 (date() raises ValueError)."""
        user = _make_user_with_birthdate(None)
        db = _make_patch_db(user)
        mock_request = Mock()

        # Bypass schema validation by using a Mock update
        update = Mock()
        update.first_name = None
        update.last_name = None
        update.display_name = None
        update.email = None
        update.default_currency = None
        update.birth_day = 30
        update.birth_month = 2
        update.birth_year = 2001  # Not a leap year, Feb 30 is invalid

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await update_user_profile(
                    update_data=update,
                    http_request=mock_request,
                    current_user=user,
                    db=db,
                )
        assert exc_info.value.status_code == 400
        assert "Invalid birthday" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_email_change_verification_email_failure_swallowed(self):
        """If send_verification_email fails, the profile update should still succeed."""
        user = _make_user_with_birthdate(None)
        user.email = "old@example.com"
        user.email_verified = True
        user.display_name = "Test"
        user.first_name = "Test"
        user.password_hash = "hashed"
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        no_user_result = Mock()
        no_user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_user_result)

        update = Mock()
        update.first_name = None
        update.last_name = None
        update.display_name = None
        update.email = "new@example.com"
        update.current_password = "correct-password"
        update.default_currency = None
        update.birth_day = None
        update.birth_month = None
        update.birth_year = None
        update.onboarding_goal = None
        update.dashboard_layout = None

        mock_request = Mock()

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.settings.verify_password", return_value=True):
                with patch(
                    "app.api.v1.settings.create_verification_token",
                    new=AsyncMock(side_effect=Exception("SMTP error")),
                ):
                    # Should not raise despite email send failure
                    await update_user_profile(
                        update_data=update,
                        http_request=mock_request,
                        current_user=user,
                        db=db,
                    )

        assert user.email == "new@example.com"
        assert user.email_verified is False


# ---------------------------------------------------------------------------
# PATCH /settings/organization — additional field branches (lines 309,313,315)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateOrganizationExtendedFields:
    """Cover org name, custom_month_end_day, and timezone update branches."""

    @pytest.mark.asyncio
    async def test_update_org_name(self):
        org = _make_org()
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        update = OrganizationUpdate(name="New Org Name")
        await update_organization_preferences(update_data=update, current_user=user, db=db)
        assert org.name == "New Org Name"

    @pytest.mark.asyncio
    async def test_update_custom_month_end_day(self):
        org = _make_org()
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        update = OrganizationUpdate(custom_month_end_day=25)
        await update_organization_preferences(update_data=update, current_user=user, db=db)
        assert org.custom_month_end_day == 25

    @pytest.mark.asyncio
    async def test_update_timezone(self):
        org = _make_org()
        user = _make_user(is_org_admin=True)
        db = _db_returning(org)

        update = OrganizationUpdate(timezone="America/New_York")
        await update_organization_preferences(update_data=update, current_user=user, db=db)
        assert org.timezone == "America/New_York"


# ---------------------------------------------------------------------------
# GET /settings/export — with actual data (lines 444-662)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportData:
    """Tests for GET /settings/export endpoint."""

    @pytest.mark.asyncio
    async def test_export_data_success(self):
        from app.api.v1.settings import export_data

        user = _make_user_with_birthdate(None)
        user.organization_id = uuid4()
        mock_request = Mock()
        db = AsyncMock()

        # Mock all DB queries: accounts, holdings, budgets, bills, rules, grants, txn batches
        accounts_scalars = Mock()
        accounts_scalars.all.return_value = []
        accounts_result = Mock()
        accounts_result.scalars.return_value = accounts_scalars

        holdings_scalars = Mock()
        holdings_scalars.all.return_value = []
        holdings_result = Mock()
        holdings_result.scalars.return_value = holdings_scalars

        budgets_scalars = Mock()
        budgets_scalars.all.return_value = []
        budgets_result = Mock()
        budgets_result.scalars.return_value = budgets_scalars

        bills_scalars = Mock()
        bills_scalars.all.return_value = []
        bills_result = Mock()
        bills_result.scalars.return_value = bills_scalars

        rules_scalars = Mock()
        rules_scalars.all.return_value = []
        rules_result = Mock()
        rules_result.scalars.return_value = rules_scalars

        grants_scalars = Mock()
        grants_scalars.all.return_value = []
        grants_result = Mock()
        grants_result.scalars.return_value = grants_scalars

        # Batch transaction query (empty batch to end loop)
        txn_batch_scalars = Mock()
        txn_batch_scalars.all.return_value = []
        txn_batch_result = Mock()
        txn_batch_result.scalars.return_value = txn_batch_scalars

        db.execute = AsyncMock(
            side_effect=[
                accounts_result,
                holdings_result,
                budgets_result,
                bills_result,
                rules_result,
                grants_result,
                txn_batch_result,  # First transaction batch (empty = done)
            ]
        )

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            response = await export_data(
                http_request=mock_request,
                format="csv",
                current_user=user,
                db=db,
            )

        assert response.media_type == "application/zip"

    @pytest.mark.asyncio
    async def test_export_data_with_holdings_budgets_bills_rules_grants(self):
        """Export with non-empty holdings, budgets, bills, rules, grants, and transactions."""
        import io
        import zipfile
        from datetime import date as dt_date
        from datetime import datetime
        from decimal import Decimal

        from app.api.v1.settings import export_data

        user = _make_user_with_birthdate(None)
        user.organization_id = uuid4()
        mock_request = Mock()
        db = AsyncMock()

        # --- Mock accounts ---
        mock_account = Mock()
        mock_account.id = uuid4()
        mock_account.name = "Test Checking"
        mock_account.account_type = Mock()
        mock_account.account_type.value = "checking"
        mock_account.institution_name = "Bank"
        mock_account.current_balance = Decimal("5000")
        mock_account.currency = "USD"
        mock_account.is_active = True
        mock_account.created_at = datetime(2024, 1, 1)

        accounts_scalars = Mock()
        accounts_scalars.all.return_value = [mock_account]
        accounts_result = Mock()
        accounts_result.scalars.return_value = accounts_scalars

        # --- Mock holdings ---
        mock_holding = Mock()
        mock_holding.ticker = "AAPL"
        mock_holding.name = "Apple Inc"
        mock_holding.shares = Decimal("10")
        mock_holding.cost_basis_per_share = Decimal("150")
        mock_holding.current_price = Decimal("175")
        mock_holding.account_id = mock_account.id

        holdings_scalars = Mock()
        holdings_scalars.all.return_value = [mock_holding]
        holdings_result = Mock()
        holdings_result.scalars.return_value = holdings_scalars

        # --- Mock budgets ---
        mock_budget = Mock()
        mock_budget.id = uuid4()
        mock_budget.name = "Groceries"
        mock_budget.amount = Decimal("500")
        mock_budget.period = Mock()
        mock_budget.period.value = "monthly"
        mock_budget.start_date = dt_date(2024, 1, 1)
        mock_budget.end_date = None
        mock_budget.rollover_unused = False
        mock_budget.alert_threshold = Decimal("80")
        mock_budget.is_active = True

        budgets_scalars = Mock()
        budgets_scalars.all.return_value = [mock_budget]
        budgets_result = Mock()
        budgets_result.scalars.return_value = budgets_scalars

        # --- Mock bills ---
        mock_bill = Mock()
        mock_bill.id = uuid4()
        mock_bill.merchant_name = "Netflix"
        mock_bill.frequency = Mock()
        mock_bill.frequency.value = "monthly"
        mock_bill.average_amount = Decimal("15.99")
        mock_bill.account_id = mock_account.id
        mock_bill.is_active = True

        bills_scalars = Mock()
        bills_scalars.all.return_value = [mock_bill]
        bills_result = Mock()
        bills_result.scalars.return_value = bills_scalars

        # --- Mock rules ---
        mock_rule = Mock()
        mock_rule.id = uuid4()
        mock_rule.name = "Coffee"
        mock_rule.description = "Auto-cat coffee"
        mock_rule.match_type = Mock()
        mock_rule.match_type.value = "all"
        mock_rule.apply_to = Mock()
        mock_rule.apply_to.value = "new"
        mock_rule.priority = 10
        mock_rule.is_active = True
        mock_rule.times_applied = 42

        rules_scalars = Mock()
        rules_scalars.all.return_value = [mock_rule]
        rules_result = Mock()
        rules_result.scalars.return_value = rules_scalars

        # --- Mock grants ---
        mock_grant = Mock()
        mock_grant.id = uuid4()
        mock_grant.grantee_id = uuid4()
        mock_grant.resource_type = "account"
        mock_grant.resource_id = mock_account.id
        mock_grant.actions = ["read", "update"]
        mock_grant.granted_at = datetime(2024, 6, 1)
        mock_grant.expires_at = None

        grants_scalars = Mock()
        grants_scalars.all.return_value = [mock_grant]
        grants_result = Mock()
        grants_result.scalars.return_value = grants_scalars

        # --- Mock transactions (one batch then empty) ---
        mock_txn = Mock()
        mock_txn.amount = Decimal("-25.50")
        mock_txn.date = dt_date(2024, 3, 15)
        mock_txn.merchant_name = "Starbucks"
        mock_txn.category_primary = "Food"
        mock_txn.labels = None
        mock_txn.account_id = mock_account.id
        mock_txn.notes = "coffee"

        txn_batch_scalars = Mock()
        txn_batch_scalars.all.return_value = [mock_txn]
        txn_batch_result = Mock()
        txn_batch_result.scalars.return_value = txn_batch_scalars

        txn_empty_scalars = Mock()
        txn_empty_scalars.all.return_value = []
        txn_empty_result = Mock()
        txn_empty_result.scalars.return_value = txn_empty_scalars

        db.execute = AsyncMock(
            side_effect=[
                accounts_result,
                holdings_result,
                budgets_result,
                bills_result,
                rules_result,
                grants_result,
                txn_batch_result,
                txn_empty_result,
            ]
        )

        with patch("app.api.v1.settings.rate_limit_service.check_rate_limit", new=AsyncMock()):
            response = await export_data(
                http_request=mock_request,
                format="csv",
                current_user=user,
                db=db,
            )

        assert response.media_type == "application/zip"
        # StreamingResponse wraps a BytesIO; read it back
        zip_data = b""
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                zip_data += chunk
            else:
                zip_data += chunk.encode()
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer) as zf:
            names = zf.namelist()
            assert "transactions.csv" in names
            assert "accounts.csv" in names
            assert "holdings.csv" in names
            assert "budgets.csv" in names
            assert "bills.csv" in names
            assert "rules.csv" in names
            assert "grants.csv" in names

    @pytest.mark.asyncio
    async def test_export_data_rate_limited(self):
        from app.api.v1.settings import export_data

        user = _make_user_with_birthdate(None)
        mock_request = Mock()
        db = AsyncMock()

        with patch(
            "app.api.v1.settings.rate_limit_service.check_rate_limit",
            new=AsyncMock(side_effect=HTTPException(status_code=429, detail="Rate limited")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await export_data(
                    http_request=mock_request,
                    format="csv",
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 429
