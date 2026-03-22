"""Tests for login_count tracking, onboarding_goal, and first-login welcome behavior."""

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


# ---------------------------------------------------------------------------
# onboarding_goal column
# ---------------------------------------------------------------------------

class TestOnboardingGoalModel:
    def test_field_exists_on_model(self):
        assert hasattr(User, "onboarding_goal")

    def test_defaults_to_none(self, fresh_user: User):
        assert fresh_user.onboarding_goal is None

    @pytest.mark.asyncio
    async def test_can_be_set_and_persisted(self, db_session: AsyncSession, fresh_user: User):
        from sqlalchemy import update as sa_update
        from app.models.user import User as UserModel

        await db_session.execute(
            sa_update(UserModel)
            .where(UserModel.id == fresh_user.id)
            .values(onboarding_goal="savings")
        )
        await db_session.commit()
        await db_session.refresh(fresh_user)
        assert fresh_user.onboarding_goal == "savings"

    @pytest.mark.asyncio
    async def test_accepts_all_valid_goal_values(self, db_session: AsyncSession, org: Organization):
        """Each supported onboarding goal string should round-trip through the DB."""
        from sqlalchemy import update as sa_update
        from app.models.user import User as UserModel

        valid_goals = ["savings", "debt", "investments", "budgeting", "retirement"]
        for goal in valid_goals:
            u = User(
                id=uuid4(),
                email=f"goal_{goal}@example.com",
                password_hash=hash_password("pw"),
                organization_id=org.id,
                is_active=True,
                is_org_admin=False,
                failed_login_attempts=0,
                locked_until=None,
                onboarding_goal=goal,
            )
            db_session.add(u)
            await db_session.commit()
            await db_session.refresh(u)
            assert u.onboarding_goal == goal, f"Expected {goal}, got {u.onboarding_goal}"

    @pytest.mark.asyncio
    async def test_can_be_cleared(self, db_session: AsyncSession, fresh_user: User):
        from sqlalchemy import update as sa_update
        from app.models.user import User as UserModel

        await db_session.execute(
            sa_update(UserModel)
            .where(UserModel.id == fresh_user.id)
            .values(onboarding_goal="debt")
        )
        await db_session.commit()
        await db_session.execute(
            sa_update(UserModel)
            .where(UserModel.id == fresh_user.id)
            .values(onboarding_goal=None)
        )
        await db_session.commit()
        await db_session.refresh(fresh_user)
        assert fresh_user.onboarding_goal is None


class TestOnboardingGoalSchema:
    def test_onboarding_goal_in_user_indb(self):
        from app.schemas.user import UserInDB
        assert "onboarding_goal" in UserInDB.model_fields

    def test_onboarding_goal_defaults_to_none_in_schema(self):
        from app.schemas.user import UserInDB
        field = UserInDB.model_fields["onboarding_goal"]
        assert field.default is None

    def test_onboarding_goal_in_user_update(self):
        from app.schemas.user import UserUpdate
        assert "onboarding_goal" in UserUpdate.model_fields

    def test_onboarding_goal_accepts_none_in_update(self):
        from app.schemas.user import UserUpdate
        patch = UserUpdate(onboarding_goal=None)
        assert patch.onboarding_goal is None

    def test_onboarding_goal_accepts_string_in_update(self):
        from app.schemas.user import UserUpdate
        patch = UserUpdate(onboarding_goal="savings")
        assert patch.onboarding_goal == "savings"


# ---------------------------------------------------------------------------
# DB migration: both columns actually exist in the live schema
# (uses SQLite PRAGMA — compatible with the test DB)
# ---------------------------------------------------------------------------

class TestMigrationApplied:
    """Verify the columns are present in the test DB (catches 'migration not run')."""

    @pytest.mark.asyncio
    async def test_login_count_column_exists_in_db(self, db_session: AsyncSession):
        from sqlalchemy import text
        result = await db_session.execute(text("PRAGMA table_info(users)"))
        columns = {row[1] for row in result.fetchall()}
        assert "login_count" in columns, \
            "login_count column missing — run: alembic upgrade head"

    @pytest.mark.asyncio
    async def test_onboarding_goal_column_exists_in_db(self, db_session: AsyncSession):
        from sqlalchemy import text
        result = await db_session.execute(text("PRAGMA table_info(users)"))
        columns = {row[1] for row in result.fetchall()}
        assert "onboarding_goal" in columns, \
            "onboarding_goal column missing — run: alembic upgrade head"
