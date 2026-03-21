"""Tests for login_count tracking and first-login welcome behavior."""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Organization
from app.crud.user import UserCRUD
from app.core.security import hash_password


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    o = Organization(id=uuid4(), name="Login Test Org")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest_asyncio.fixture
async def fresh_user(db_session: AsyncSession, org: Organization) -> User:
    """A brand-new user who has never logged in (login_count=0)."""
    u = User(
        id=uuid4(),
        email="fresh@example.com",
        password_hash=hash_password("pw"),
        organization_id=org.id,
        is_active=True,
        is_org_admin=False,
        failed_login_attempts=0,
        locked_until=None,
        login_count=0,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


# ---------------------------------------------------------------------------
# login_count model defaults
# ---------------------------------------------------------------------------

class TestLoginCountModel:
    def test_default_is_zero(self, fresh_user: User):
        assert fresh_user.login_count == 0

    def test_field_exists_on_model(self):
        assert hasattr(User, "login_count")


# ---------------------------------------------------------------------------
# UserCRUD.update_last_login increments login_count
# ---------------------------------------------------------------------------

class TestUpdateLastLogin:
    @pytest.mark.asyncio
    async def test_increments_on_first_call(self, db_session: AsyncSession, fresh_user: User):
        await UserCRUD.update_last_login(db_session, fresh_user.id)
        await db_session.refresh(fresh_user)
        assert fresh_user.login_count == 1

    @pytest.mark.asyncio
    async def test_increments_on_subsequent_calls(self, db_session: AsyncSession, fresh_user: User):
        await UserCRUD.update_last_login(db_session, fresh_user.id)
        await UserCRUD.update_last_login(db_session, fresh_user.id)
        await UserCRUD.update_last_login(db_session, fresh_user.id)
        await db_session.refresh(fresh_user)
        assert fresh_user.login_count == 3

    @pytest.mark.asyncio
    async def test_also_sets_last_login_at(self, db_session: AsyncSession, fresh_user: User):
        assert fresh_user.last_login_at is None
        await UserCRUD.update_last_login(db_session, fresh_user.id)
        await db_session.refresh(fresh_user)
        assert fresh_user.last_login_at is not None

    @pytest.mark.asyncio
    async def test_handles_null_login_count_gracefully(self, db_session: AsyncSession, org: Organization):
        """If login_count is NULL in the DB (pre-migration rows), it should still increment."""
        u = User(
            id=uuid4(),
            email="nullcount@example.com",
            password_hash=hash_password("pw"),
            organization_id=org.id,
            is_active=True,
            is_org_admin=False,
            failed_login_attempts=0,
            locked_until=None,
            login_count=None,  # simulate pre-migration row
        )
        db_session.add(u)
        await db_session.commit()

        await UserCRUD.update_last_login(db_session, u.id)
        await db_session.refresh(u)
        assert u.login_count == 1

    @pytest.mark.asyncio
    async def test_noop_for_unknown_user_id(self, db_session: AsyncSession):
        """Should not raise if user_id doesn't exist."""
        await UserCRUD.update_last_login(db_session, uuid4())  # no error


# ---------------------------------------------------------------------------
# Schema exposes login_count
# ---------------------------------------------------------------------------

class TestUserSchema:
    def test_login_count_in_schema(self):
        from app.schemas.user import UserInDB
        fields = UserInDB.model_fields
        assert "login_count" in fields

    def test_login_count_defaults_to_zero_in_schema(self):
        from app.schemas.user import UserInDB
        field = UserInDB.model_fields["login_count"]
        assert field.default == 0


# ---------------------------------------------------------------------------
# Welcome message logic (mirrors the frontend condition)
# ---------------------------------------------------------------------------

class TestWelcomeMessageLogic:
    """Verify the condition used on the dashboard: login_count <= 1 → 'Welcome', else 'Welcome back'."""

    def _greeting(self, login_count: int) -> str:
        return "Welcome" if login_count <= 1 else "Welcome back"

    def test_first_login_shows_welcome(self):
        assert self._greeting(1) == "Welcome"

    def test_zero_count_shows_welcome(self):
        # Defensive: should never happen in practice but guard against it
        assert self._greeting(0) == "Welcome"

    def test_second_login_shows_welcome_back(self):
        assert self._greeting(2) == "Welcome back"

    def test_many_logins_shows_welcome_back(self):
        assert self._greeting(50) == "Welcome back"
