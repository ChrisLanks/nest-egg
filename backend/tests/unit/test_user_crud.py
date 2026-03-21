"""Unit tests for user CRUD operations."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.crud.user import OrganizationCRUD, RefreshTokenCRUD, UserCRUD


@pytest.mark.unit
class TestUserCRUD:
    """Test UserCRUD operations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_by_email_found(self, mock_db):
        user = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = result_mock

        result = await UserCRUD.get_by_email(mock_db, "test@example.com")
        assert result == user

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, mock_db):
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await UserCRUD.get_by_email(mock_db, "missing@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_db):
        user = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = result_mock

        result = await UserCRUD.get_by_id(mock_db, uuid4())
        assert result == user

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_db):
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await UserCRUD.get_by_id(mock_db, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_create_with_full_birthdate(self, mock_db):
        """Full birthdate (year, month, day) creates proper date."""
        org_id = uuid4()

        with patch("app.crud.user.hash_password", return_value="hashed_pw"):
            with patch("app.crud.user.User") as MockUser:
                MockUser.return_value = Mock()
                await UserCRUD.create(
                    mock_db,
                    "test@example.com",
                    "password123",
                    org_id,
                    birth_year=1990,
                    birth_month=5,
                    birth_day=15,
                )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_with_year_month_only(self, mock_db):
        """Year and month only creates date with day=1."""
        org_id = uuid4()

        with patch("app.crud.user.hash_password", return_value="hashed_pw"):
            with patch("app.crud.user.User") as MockUser:
                MockUser.return_value = Mock()
                await UserCRUD.create(
                    mock_db,
                    "test@example.com",
                    "password123",
                    org_id,
                    birth_year=1990,
                    birth_month=5,
                )

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_year_only(self, mock_db):
        """Year only creates date with month=1, day=1."""
        org_id = uuid4()

        with patch("app.crud.user.hash_password", return_value="hashed_pw"):
            with patch("app.crud.user.User") as MockUser:
                MockUser.return_value = Mock()
                await UserCRUD.create(
                    mock_db, "test@example.com", "password123", org_id, birth_year=1990
                )

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_without_birthdate(self, mock_db):
        """No birth info results in None birthdate."""
        org_id = uuid4()

        with patch("app.crud.user.hash_password", return_value="hashed_pw"):
            with patch("app.crud.user.User") as MockUser:
                MockUser.return_value = Mock()
                await UserCRUD.create(mock_db, "test@example.com", "password123", org_id)

        # Verify User was called with birthdate=None
        call_kwargs = MockUser.call_args[1]
        assert call_kwargs["birthdate"] is None

    @pytest.mark.asyncio
    async def test_create_with_all_optional_fields(self, mock_db):
        """All optional fields passed through."""
        org_id = uuid4()

        with patch("app.crud.user.hash_password", return_value="hashed_pw"):
            with patch("app.crud.user.User") as MockUser:
                MockUser.return_value = Mock()
                await UserCRUD.create(
                    mock_db,
                    "test@example.com",
                    "password123",
                    org_id,
                    first_name="John",
                    last_name="Doe",
                    display_name="JD",
                    is_org_admin=True,
                )

        call_kwargs = MockUser.call_args[1]
        assert call_kwargs["first_name"] == "John"
        assert call_kwargs["last_name"] == "Doe"
        assert call_kwargs["display_name"] == "JD"
        assert call_kwargs["is_org_admin"] is True

    @pytest.mark.asyncio
    async def test_update_last_login_user_found(self, mock_db):
        """Updates last_login_at when user exists."""
        user = Mock()
        user.login_count = 3
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = result_mock

        await UserCRUD.update_last_login(mock_db, uuid4())

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_last_login_user_not_found(self, mock_db):
        """No-op when user not found."""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        await UserCRUD.update_last_login(mock_db, uuid4())

        mock_db.commit.assert_not_awaited()


@pytest.mark.unit
class TestOrganizationCRUD:
    """Test OrganizationCRUD operations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_create(self, mock_db):
        with patch("app.crud.user.Organization") as MockOrg:
            MockOrg.return_value = Mock()
            await OrganizationCRUD.create(mock_db, "Test Org")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_with_custom_params(self, mock_db):
        with patch("app.crud.user.Organization") as MockOrg:
            MockOrg.return_value = Mock()
            await OrganizationCRUD.create(
                mock_db, "Test Org", custom_month_end_day=15, timezone="US/Eastern"
            )

        call_kwargs = MockOrg.call_args[1]
        assert call_kwargs["custom_month_end_day"] == 15
        assert call_kwargs["timezone"] == "US/Eastern"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_db):
        org = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = org
        mock_db.execute.return_value = result_mock

        result = await OrganizationCRUD.get_by_id(mock_db, uuid4())
        assert result == org

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_db):
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await OrganizationCRUD.get_by_id(mock_db, uuid4())
        assert result is None


@pytest.mark.unit
class TestRefreshTokenCRUD:
    """Test RefreshTokenCRUD operations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_create(self, mock_db):
        with patch("app.crud.user.RefreshToken") as MockToken:
            MockToken.return_value = Mock()
            await RefreshTokenCRUD.create(mock_db, uuid4(), "token_hash", datetime.now())

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_token_hash_found(self, mock_db):
        token = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = token
        mock_db.execute.return_value = result_mock

        result = await RefreshTokenCRUD.get_by_token_hash(mock_db, "hash123")
        assert result == token

    @pytest.mark.asyncio
    async def test_get_by_token_hash_not_found(self, mock_db):
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await RefreshTokenCRUD.get_by_token_hash(mock_db, "missing_hash")
        assert result is None

    @pytest.mark.asyncio
    async def test_revoke_found(self, mock_db):
        token = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = token
        mock_db.execute.return_value = result_mock

        await RefreshTokenCRUD.revoke(mock_db, "hash123")

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_revoke_not_found(self, mock_db):
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        await RefreshTokenCRUD.revoke(mock_db, "missing_hash")

        mock_db.commit.assert_not_awaited()
