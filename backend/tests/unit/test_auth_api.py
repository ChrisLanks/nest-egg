"""Unit tests for auth API endpoints."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import HTTPException, status

from app.models.user import User, Organization
from app.utils.datetime_utils import utc_now


@pytest.mark.unit
class TestCreateAuthResponse:
    """Test create_auth_response helper function."""

    @pytest.mark.asyncio
    async def test_create_auth_response_generates_tokens(self):
        """Should generate access and refresh tokens."""
        from app.api.v1.auth import create_auth_response
        from app.schemas.user import User as UserSchema

        mock_db = AsyncMock()
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"

        mock_user_schema = Mock(spec=UserSchema)

        with patch("app.api.v1.auth.create_access_token") as mock_access:
            with patch("app.api.v1.auth.create_refresh_token") as mock_refresh:
                with patch("app.api.v1.auth.refresh_token_crud.create", new=AsyncMock()):
                    with patch("app.schemas.user.User.from_orm", return_value=mock_user_schema):
                        mock_access.return_value = "access_token_123"
                        mock_refresh.return_value = ("refresh_token_123", "jti_123", datetime.now())

                        result = await create_auth_response(mock_db, mock_user)

                        assert result.access_token == "access_token_123"
                        assert result.refresh_token == "refresh_token_123"

    @pytest.mark.asyncio
    async def test_create_auth_response_stores_refresh_token(self):
        """Should store refresh token hash in database."""
        from app.api.v1.auth import create_auth_response
        from app.schemas.user import User as UserSchema

        mock_db = AsyncMock()
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"

        mock_user_schema = Mock(spec=UserSchema)

        with patch("app.api.v1.auth.create_access_token", return_value="access"):
            with patch("app.api.v1.auth.create_refresh_token", return_value=("refresh", "jti", datetime.now())):
                with patch("app.api.v1.auth.refresh_token_crud.create", new=AsyncMock()) as mock_create:
                    with patch("app.schemas.user.User.from_orm", return_value=mock_user_schema):
                        await create_auth_response(mock_db, mock_user)

                        assert mock_create.called


@pytest.mark.unit
class TestRegisterEndpoint:
    """Test /auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_enforces_rate_limit(self):
        """Should check rate limit before processing."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.password = "SecurePass123!"
        mock_data.email = "test@example.com"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()) as mock_rate_limit:
            mock_rate_limit.side_effect = HTTPException(status_code=429, detail="Rate limit exceeded")

            with pytest.raises(HTTPException) as exc_info:
                await register(mock_request, mock_data, mock_db)

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_register_validates_password_strength(self):
        """Should validate password strength and check for breaches."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.password = "weak"
        mock_data.email = "test@example.com"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()) as mock_validate:
                mock_validate.side_effect = ValueError("Password too weak")

                with pytest.raises(ValueError):
                    await register(mock_request, mock_data, mock_db)

    @pytest.mark.asyncio
    async def test_register_rejects_duplicate_email(self):
        """Should reject registration with existing email."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "existing@example.com"
        mock_data.password = "SecurePass123!"

        mock_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=mock_user)):
                    with pytest.raises(HTTPException) as exc_info:
                        await register(mock_request, mock_data, mock_db)

                    assert exc_info.value.status_code == 400
                    assert "already registered" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_register_creates_organization_and_user(self):
        """Should create both organization and user."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "new@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.organization_name = "New Org"
        mock_data.first_name = "New"
        mock_data.last_name = "User"
        mock_data.display_name = None

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "new@example.com"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)) as mock_org_create:
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)) as mock_user_create:
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()) as mock_auth_response:
                                    await register(mock_request, mock_data, mock_db)

                                    assert mock_org_create.called
                                    assert mock_user_create.called

    @pytest.mark.asyncio
    async def test_register_sets_first_user_as_admin(self):
        """Should set first user as org admin."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "admin@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.organization_name = "New Org"
        mock_data.first_name = "Admin"
        mock_data.last_name = "User"
        mock_data.display_name = None

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)):
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)) as mock_create:
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    call_kwargs = mock_create.call_args.kwargs
                                    assert call_kwargs.get("is_org_admin") is True

    @pytest.mark.asyncio
    async def test_register_derives_org_name_from_display_name_when_default(self):
        """When organization_name is the default 'My Household', use '{display_name}'s Household'."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "jane@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.organization_name = "My Household"  # the schema default
        mock_data.display_name = "Jane"
        mock_data.first_name = None
        mock_data.last_name = None

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)) as mock_org_create:
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)):
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    call_kwargs = mock_org_create.call_args.kwargs
                                    assert call_kwargs["name"] == "Jane's Household"

    @pytest.mark.asyncio
    async def test_register_uses_explicit_org_name_when_provided(self):
        """When a non-default organization_name is provided, use it as-is."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "bob@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.organization_name = "Smith Family Trust"
        mock_data.first_name = "Bob"
        mock_data.last_name = "Smith"

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)) as mock_org_create:
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)):
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    call_kwargs = mock_org_create.call_args.kwargs
                                    assert call_kwargs["name"] == "Smith Family Trust"

    @pytest.mark.asyncio
    async def test_register_stores_display_name_when_provided(self):
        """display_name provided at registration should be saved on the user."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "alex@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.organization_name = "My Household"
        mock_data.first_name = "Alex"
        mock_data.last_name = None
        mock_data.display_name = "Lex"

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)):
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)) as mock_create:
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    call_kwargs = mock_create.call_args.kwargs
                                    assert call_kwargs.get("display_name") == "Lex"

    @pytest.mark.asyncio
    async def test_register_works_without_last_name(self):
        """last_name is optional — registration must succeed when omitted."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "solo@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.organization_name = "My Household"
        mock_data.display_name = "Solo"
        mock_data.first_name = None
        mock_data.last_name = None
        mock_data.birth_month = None
        mock_data.birth_year = None

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)) as mock_org_create:
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)) as mock_create:
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    call_kwargs = mock_create.call_args.kwargs
                                    assert call_kwargs.get("last_name") is None
                                    # org name derived from display_name when default used
                                    org_call_kwargs = mock_org_create.call_args.kwargs
                                    assert org_call_kwargs["name"] == "Solo's Household"

    @pytest.mark.asyncio
    async def test_register_stores_birthday_when_provided(self):
        """birth_day + birth_month + birth_year at registration should be passed to user_crud.create()."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "young@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.organization_name = "My Household"
        mock_data.display_name = "Young"
        mock_data.first_name = None
        mock_data.last_name = None
        mock_data.birth_day = 15
        mock_data.birth_month = 6
        mock_data.birth_year = 1990

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)):
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)) as mock_create:
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    call_kwargs = mock_create.call_args.kwargs
                                    assert call_kwargs.get("birth_day") == 15
                                    assert call_kwargs.get("birth_month") == 6
                                    assert call_kwargs.get("birth_year") == 1990

    @pytest.mark.asyncio
    async def test_register_omits_birthday_when_not_provided(self):
        """birthday is optional — None should be passed for all fields when omitted."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "no_bday@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.organization_name = "My Household"
        mock_data.display_name = "NoBday"
        mock_data.first_name = None
        mock_data.last_name = None
        mock_data.birth_day = None
        mock_data.birth_month = None
        mock_data.birth_year = None

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)):
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)) as mock_create:
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    call_kwargs = mock_create.call_args.kwargs
                                    assert call_kwargs.get("birth_day") is None
                                    assert call_kwargs.get("birth_month") is None
                                    assert call_kwargs.get("birth_year") is None


@pytest.mark.unit
class TestRegisterRequestSchema:
    """Test RegisterRequest schema validation for birthday fields."""

    def test_birthday_optional_absent(self):
        """All birthday fields omitted → all None."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            email="a@example.com",
            password="SecurePass123!",
            display_name="Alice",
        )
        assert req.birth_day is None
        assert req.birth_month is None
        assert req.birth_year is None

    def test_birthday_valid_with_full_date(self):
        """Valid birth_day, birth_month, and birth_year are accepted."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            email="a@example.com",
            password="SecurePass123!",
            display_name="Alice",
            birth_day=15,
            birth_month=6,
            birth_year=1985,
        )
        assert req.birth_day == 15
        assert req.birth_month == 6
        assert req.birth_year == 1985

    def test_birth_day_too_low_rejected(self):
        """birth_day < 1 is rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_day=0,
                birth_month=6,
                birth_year=1990,
            )

    def test_birth_day_too_high_rejected(self):
        """birth_day > 31 is rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_day=32,
                birth_month=6,
                birth_year=1990,
            )

    def test_birth_year_too_low_rejected(self):
        """birth_year < 1900 is rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_day=1,
                birth_month=1,
                birth_year=1899,
            )

    def test_birth_year_too_high_rejected(self):
        """birth_year > 2100 is rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_month=1,
                birth_year=2101,
            )

    def test_birth_month_too_low_rejected(self):
        """birth_month < 1 is rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_month=0,
                birth_year=1990,
            )

    def test_birth_month_too_high_rejected(self):
        """birth_month > 12 is rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_month=13,
                birth_year=1990,
            )

    def test_birth_year_boundary_1900_accepted(self):
        """Birth year 1900 (lower bound) is valid."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            email="a@example.com",
            password="SecurePass123!",
            display_name="Alice",
            birth_month=1,
            birth_year=1900,
        )
        assert req.birth_year == 1900

    def test_birth_year_boundary_2100_accepted(self):
        """Birth year 2100 (upper bound) is valid."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            email="a@example.com",
            password="SecurePass123!",
            display_name="Alice",
            birth_month=12,
            birth_year=2100,
        )
        assert req.birth_year == 2100

    def test_feb_30_rejected(self):
        """Feb 30 is an impossible date and must be rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_day=30,
                birth_month=2,
                birth_year=1990,
            )

    def test_feb_29_on_non_leap_year_rejected(self):
        """Feb 29 on a non-leap year is rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_day=29,
                birth_month=2,
                birth_year=1990,  # 1990 is not a leap year
            )

    def test_feb_29_on_leap_year_accepted(self):
        """Feb 29 on a leap year is valid."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            email="a@example.com",
            password="SecurePass123!",
            display_name="Alice",
            birth_day=29,
            birth_month=2,
            birth_year=1992,  # 1992 is a leap year
        )
        assert req.birth_day == 29
        assert req.birth_month == 2
        assert req.birth_year == 1992

    def test_apr_31_rejected(self):
        """April 31 is an impossible date and must be rejected."""
        from app.schemas.auth import RegisterRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegisterRequest(
                email="a@example.com",
                password="SecurePass123!",
                display_name="Alice",
                birth_day=31,
                birth_month=4,
                birth_year=1990,
            )

    def test_skip_password_validation_defaults_to_false(self):
        """skip_password_validation should default to False."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            email="a@example.com",
            password="SecurePass123!",
            display_name="Alice",
        )
        assert req.skip_password_validation is False

    def test_skip_password_validation_can_be_set_true(self):
        """skip_password_validation=True should be accepted."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            email="a@example.com",
            password="SecurePass123!",
            display_name="Alice",
            skip_password_validation=True,
        )
        assert req.skip_password_validation is True


@pytest.mark.unit
class TestSkipPasswordValidation:
    """Test skip_password_validation flag behaviour on register endpoint."""

    @pytest.mark.asyncio
    async def test_skip_validation_true_bypasses_password_check(self):
        """When skip_password_validation=True, validation service is NOT called."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "new@example.com"
        mock_data.password = "bad"
        mock_data.skip_password_validation = True
        mock_data.organization_name = "My Household"
        mock_data.display_name = "Alice"
        mock_data.first_name = None
        mock_data.last_name = None
        mock_data.birth_day = None
        mock_data.birth_month = None
        mock_data.birth_year = None

        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()) as mock_validate:
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=mock_org)):
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=mock_user)):
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    # Validation service must NOT be called when flag is set
                                    mock_validate.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_validation_false_still_validates_password(self):
        """When skip_password_validation=False (default), validation service IS called."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "new@example.com"
        mock_data.password = "SecurePass123!"
        mock_data.skip_password_validation = False

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()) as mock_validate:
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                    with patch("app.api.v1.auth.organization_crud.create", new=AsyncMock(return_value=Mock(id=uuid4()))):
                        with patch("app.api.v1.auth.user_crud.create", new=AsyncMock(return_value=Mock(id=uuid4()))):
                            with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                                with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                                    await register(mock_request, mock_data, mock_db)

                                    # Validation service MUST be called when flag is not set
                                    mock_validate.assert_called_once_with(
                                        mock_data.password, check_breach=True
                                    )

    @pytest.mark.asyncio
    async def test_skip_validation_true_still_checks_duplicate_email(self):
        """skip_password_validation bypasses password checks but still blocks duplicate emails."""
        from app.api.v1.auth import register

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "existing@example.com"
        mock_data.password = "bad"
        mock_data.skip_password_validation = True

        existing_user = Mock(spec=User)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.password_validation_service.validate_and_raise_async", new=AsyncMock()):
                with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=existing_user)):
                    with pytest.raises(HTTPException) as exc_info:
                        await register(mock_request, mock_data, mock_db)

                    assert exc_info.value.status_code == 400
                    assert "already registered" in exc_info.value.detail.lower()


@pytest.mark.unit
class TestUserCRUDBirthday:
    """Test user_crud.create() converts birth_month + birth_year to birthdate correctly."""

    @pytest.mark.asyncio
    async def test_create_sets_birthdate_from_full_birthday(self):
        """birth_day + birth_month + birth_year converts to exact date stored on user."""
        from app.crud.user import UserCRUD
        from datetime import date

        mock_db = AsyncMock()
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        captured_user = None

        def capture_add(user):
            nonlocal captured_user
            captured_user = user

        mock_db.add.side_effect = capture_add

        with patch("app.crud.user.hash_password", return_value="hashed"):
            await UserCRUD.create(
                db=mock_db,
                email="test@example.com",
                password="password",
                organization_id=uuid4(),
                display_name="Test",
                birth_day=15,
                birth_month=6,
                birth_year=1990,
            )

        assert captured_user is not None
        assert captured_user.birthdate == date(1990, 6, 15)

    @pytest.mark.asyncio
    async def test_create_sets_birthdate_from_year_only(self):
        """birth_year without birth_month defaults to January (month=1)."""
        from app.crud.user import UserCRUD
        from datetime import date

        mock_db = AsyncMock()
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        captured_user = None

        def capture_add(user):
            nonlocal captured_user
            captured_user = user

        mock_db.add.side_effect = capture_add

        with patch("app.crud.user.hash_password", return_value="hashed"):
            await UserCRUD.create(
                db=mock_db,
                email="test@example.com",
                password="password",
                organization_id=uuid4(),
                display_name="Test",
                birth_year=1990,
            )

        assert captured_user is not None
        assert captured_user.birthdate == date(1990, 1, 1)

    @pytest.mark.asyncio
    async def test_create_leaves_birthdate_none_when_birthday_omitted(self):
        """No birthday fields → birthdate is None."""
        from app.crud.user import UserCRUD

        mock_db = AsyncMock()
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        captured_user = None

        def capture_add(user):
            nonlocal captured_user
            captured_user = user

        mock_db.add.side_effect = capture_add

        with patch("app.crud.user.hash_password", return_value="hashed"):
            await UserCRUD.create(
                db=mock_db,
                email="test@example.com",
                password="password",
                organization_id=uuid4(),
                display_name="Test",
            )

        assert captured_user is not None
        assert captured_user.birthdate is None


@pytest.mark.unit
class TestLoginEndpoint:
    """Test /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_enforces_rate_limit(self):
        """Should check rate limit before processing."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "test@example.com"
        mock_data.password = "password"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()) as mock_rate_limit:
            mock_rate_limit.side_effect = HTTPException(status_code=429)

            with pytest.raises(HTTPException) as exc_info:
                await login(mock_request, mock_data, mock_db)

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_login_performs_timing_attack_prevention(self):
        """Should perform dummy password check for non-existent users."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "nonexistent@example.com"
        mock_data.password = "password"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=None)):
                with patch("app.api.v1.auth.verify_password") as mock_verify:
                    with pytest.raises(HTTPException) as exc_info:
                        await login(mock_request, mock_data, mock_db)

                    # Should still call verify_password for timing consistency
                    assert mock_verify.called
                    assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_checks_account_lockout(self):
        """Should reject login for locked accounts."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "locked@example.com"
        mock_data.password = "password"

        mock_user = Mock(spec=User)
        mock_user.locked_until = utc_now() + timedelta(minutes=30)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=mock_user)):
                with pytest.raises(HTTPException) as exc_info:
                    await login(mock_request, mock_data, mock_db)

                assert exc_info.value.status_code == 403
                assert "locked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_login_resets_expired_lockout(self):
        """Should reset lockout if period has expired."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "user@example.com"
        mock_data.password = "password"

        mock_user = Mock(spec=User)
        mock_user.locked_until = utc_now() - timedelta(minutes=1)  # Expired
        mock_user.failed_login_attempts = 5
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_user.id = uuid4()
        mock_user.email = "user@example.com"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=mock_user)):
                with patch("app.api.v1.auth.verify_password", return_value=True):
                    with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                        with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                            await login(mock_request, mock_data, mock_db)

                            # Should reset failed attempts
                            assert mock_user.failed_login_attempts == 0
                            assert mock_user.locked_until is None

    @pytest.mark.asyncio
    async def test_login_increments_failed_attempts_on_wrong_password(self):
        """Should increment failed login attempts on wrong password."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "user@example.com"
        mock_data.password = "wrongpassword"

        mock_user = Mock(spec=User)
        mock_user.failed_login_attempts = 2
        mock_user.password_hash = "hashed"
        mock_user.locked_until = None

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=mock_user)):
                with patch("app.api.v1.auth.verify_password", return_value=False):
                    with pytest.raises(HTTPException) as exc_info:
                        await login(mock_request, mock_data, mock_db)

                    assert mock_user.failed_login_attempts == 3
                    assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_locks_account_after_max_attempts(self):
        """Should lock account after max failed attempts."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "user@example.com"
        mock_data.password = "wrongpassword"

        mock_user = Mock(spec=User)
        mock_user.failed_login_attempts = 4  # One before max
        mock_user.password_hash = "hashed"
        mock_user.locked_until = None

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=mock_user)):
                with patch("app.api.v1.auth.verify_password", return_value=False):
                    with patch("app.api.v1.auth.settings.MAX_LOGIN_ATTEMPTS", 5):
                        with patch("app.api.v1.auth.settings.ACCOUNT_LOCKOUT_MINUTES", 30):
                            with pytest.raises(HTTPException) as exc_info:
                                await login(mock_request, mock_data, mock_db)

                            assert mock_user.failed_login_attempts == 5
                            assert mock_user.locked_until is not None
                            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_login_rejects_inactive_user(self):
        """Should reject login for inactive users."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "inactive@example.com"
        mock_data.password = "password"

        mock_user = Mock(spec=User)
        mock_user.is_active = False
        mock_user.password_hash = "hashed"
        mock_user.failed_login_attempts = 0
        mock_user.locked_until = None

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=mock_user)):
                with patch("app.api.v1.auth.verify_password", return_value=True):
                    with pytest.raises(HTTPException) as exc_info:
                        await login(mock_request, mock_data, mock_db)

                    assert exc_info.value.status_code == 403
                    assert "inactive" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_login_success_resets_failed_attempts(self):
        """Should reset failed attempts on successful login."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "user@example.com"
        mock_data.password = "correctpassword"

        mock_user = Mock(spec=User)
        mock_user.failed_login_attempts = 3
        mock_user.locked_until = None
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_user.id = uuid4()
        mock_user.email = "user@example.com"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(return_value=mock_user)):
                with patch("app.api.v1.auth.verify_password", return_value=True):
                    with patch("app.api.v1.auth.user_crud.update_last_login", new=AsyncMock()):
                        with patch("app.api.v1.auth.create_auth_response", new=AsyncMock()):
                            await login(mock_request, mock_data, mock_db)

                            assert mock_user.failed_login_attempts == 0
                            assert mock_user.locked_until is None

    @pytest.mark.asyncio
    async def test_login_handles_exceptions(self):
        """Should handle unexpected exceptions gracefully."""
        from app.api.v1.auth import login

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.email = "user@example.com"
        mock_data.password = "password"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.user_crud.get_by_email", new=AsyncMock(side_effect=Exception("DB error"))):
                with pytest.raises(HTTPException) as exc_info:
                    await login(mock_request, mock_data, mock_db)

                assert exc_info.value.status_code == 500


@pytest.mark.unit
class TestRefreshTokenEndpoint:
    """Test /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_enforces_rate_limit(self):
        """Should check rate limit before processing."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "token"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()) as mock_rate_limit:
            mock_rate_limit.side_effect = HTTPException(status_code=429)

            with pytest.raises(HTTPException) as exc_info:
                await refresh_access_token(mock_request, mock_data, mock_db)

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_refresh_rejects_invalid_token_type(self):
        """Should reject tokens that aren't refresh tokens."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "access_token"

        mock_payload = {"type": "access", "sub": str(uuid4()), "jti": "jti123"}

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with pytest.raises(HTTPException) as exc_info:
                    await refresh_access_token(mock_request, mock_data, mock_db)

                assert exc_info.value.status_code == 401
                assert "invalid token type" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_refresh_rejects_missing_jti(self):
        """Should reject tokens without JTI."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "token"

        mock_payload = {"type": "refresh", "sub": str(uuid4())}  # Missing jti

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with pytest.raises(HTTPException) as exc_info:
                    await refresh_access_token(mock_request, mock_data, mock_db)

                assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_rejects_token_not_in_database(self):
        """Should reject tokens not found in database."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "token"

        mock_payload = {"type": "refresh", "sub": str(uuid4()), "jti": "jti123"}

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with patch("app.api.v1.auth.refresh_token_crud.get_by_token_hash", new=AsyncMock(return_value=None)):
                    with pytest.raises(HTTPException) as exc_info:
                        await refresh_access_token(mock_request, mock_data, mock_db)

                    assert exc_info.value.status_code == 401
                    assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_refresh_rejects_token_without_jti(self):
        """Should reject tokens without jti (takes else branch in logging when DEBUG=False)."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "token"

        # Payload without jti (None)
        mock_payload = {"type": "refresh", "sub": str(uuid4()), "jti": None}

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with patch("app.api.v1.auth.refresh_token_crud.get_by_token_hash", new=AsyncMock(return_value=None)):
                    # Patch settings where it's used in auth.py
                    with patch("app.api.v1.auth.settings") as mock_settings:
                        mock_settings.DEBUG = False

                        with pytest.raises(HTTPException) as exc_info:
                            await refresh_access_token(mock_request, mock_data, mock_db)

                        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_rejects_revoked_token(self):
        """Should reject revoked tokens."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "token"

        mock_payload = {"type": "refresh", "sub": str(uuid4()), "jti": "jti123"}
        mock_token = Mock()
        mock_token.is_revoked = True
        mock_token.user_id = uuid4()

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with patch("app.api.v1.auth.refresh_token_crud.get_by_token_hash", new=AsyncMock(return_value=mock_token)):
                    with pytest.raises(HTTPException) as exc_info:
                        await refresh_access_token(mock_request, mock_data, mock_db)

                    assert exc_info.value.status_code == 401
                    assert "revoked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_refresh_rejects_expired_token(self):
        """Should reject expired tokens."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "token"

        mock_payload = {"type": "refresh", "sub": str(uuid4()), "jti": "jti123"}
        mock_token = Mock()
        mock_token.is_revoked = False
        mock_token.is_expired = True
        mock_token.user_id = uuid4()
        mock_token.expires_at = utc_now() - timedelta(days=1)

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with patch("app.api.v1.auth.refresh_token_crud.get_by_token_hash", new=AsyncMock(return_value=mock_token)):
                    with pytest.raises(HTTPException) as exc_info:
                        await refresh_access_token(mock_request, mock_data, mock_db)

                    assert exc_info.value.status_code == 401
                    assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_refresh_rejects_inactive_user(self):
        """Should reject refresh for inactive users."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "token"

        user_id = uuid4()
        mock_payload = {"type": "refresh", "sub": str(user_id), "jti": "jti123"}
        mock_token = Mock()
        mock_token.is_revoked = False
        mock_token.is_expired = False
        mock_token.user_id = user_id

        mock_user = Mock(spec=User)
        mock_user.is_active = False

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with patch("app.api.v1.auth.refresh_token_crud.get_by_token_hash", new=AsyncMock(return_value=mock_token)):
                    with patch("app.api.v1.auth.user_crud.get_by_id", new=AsyncMock(return_value=mock_user)):
                        with pytest.raises(HTTPException) as exc_info:
                            await refresh_access_token(mock_request, mock_data, mock_db)

                        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_success_returns_new_access_token(self):
        """Should return new access token on successful refresh."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "token"

        user_id = uuid4()
        mock_payload = {"type": "refresh", "sub": str(user_id), "jti": "jti123"}
        mock_token = Mock()
        mock_token.is_revoked = False
        mock_token.is_expired = False
        mock_token.user_id = user_id

        mock_user = Mock(spec=User)
        mock_user.is_active = True
        mock_user.id = user_id
        mock_user.email = "user@example.com"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with patch("app.api.v1.auth.refresh_token_crud.get_by_token_hash", new=AsyncMock(return_value=mock_token)):
                    with patch("app.api.v1.auth.user_crud.get_by_id", new=AsyncMock(return_value=mock_user)):
                        with patch("app.api.v1.auth.create_access_token", return_value="new_access_token"):
                            result = await refresh_access_token(mock_request, mock_data, mock_db)

                            assert result.access_token == "new_access_token"

    @pytest.mark.asyncio
    async def test_refresh_handles_decode_errors(self):
        """Should handle token decode errors."""
        from app.api.v1.auth import refresh_access_token

        mock_request = Mock()
        mock_db = AsyncMock()
        mock_data = Mock()
        mock_data.refresh_token = "invalid_token"

        with patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.auth.decode_token", side_effect=Exception("Decode error")):
                with pytest.raises(HTTPException) as exc_info:
                    await refresh_access_token(mock_request, mock_data, mock_db)

                assert exc_info.value.status_code == 401


@pytest.mark.unit
class TestLogoutEndpoint:
    """Test /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(self):
        """Should revoke the refresh token."""
        from app.api.v1.auth import logout

        mock_db = AsyncMock()
        mock_user = Mock(spec=User)
        mock_data = Mock()
        mock_data.refresh_token = "valid_token"

        mock_payload = {"jti": "jti123"}

        with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
            with patch("app.api.v1.auth.refresh_token_crud.revoke", new=AsyncMock()) as mock_revoke:
                result = await logout(mock_data, mock_db, mock_user)

                assert mock_revoke.called
                assert result is None

    @pytest.mark.asyncio
    async def test_logout_handles_invalid_token_gracefully(self):
        """Should not error on invalid token."""
        from app.api.v1.auth import logout

        mock_db = AsyncMock()
        mock_user = Mock(spec=User)
        mock_data = Mock()
        mock_data.refresh_token = "invalid_token"

        with patch("app.api.v1.auth.decode_token", side_effect=Exception("Invalid")):
            result = await logout(mock_data, mock_db, mock_user)

            # Should succeed silently
            assert result is None

    @pytest.mark.asyncio
    async def test_logout_handles_missing_jti(self):
        """Should handle tokens without JTI gracefully."""
        from app.api.v1.auth import logout

        mock_db = AsyncMock()
        mock_user = Mock(spec=User)
        mock_data = Mock()
        mock_data.refresh_token = "token"

        mock_payload = {}  # No jti

        with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
            with patch("app.api.v1.auth.refresh_token_crud.revoke", new=AsyncMock()) as mock_revoke:
                result = await logout(mock_data, mock_db, mock_user)

                # Should not attempt to revoke
                assert not mock_revoke.called
                assert result is None


@pytest.mark.unit
class TestGetCurrentUserEndpoint:
    """Test /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_returns_user_schema(self):
        """Should return current user information."""
        from app.api.v1.auth import get_current_user_info
        from app.schemas.user import User as UserSchema

        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"

        mock_user_schema = Mock(spec=UserSchema)

        with patch.object(UserSchema, "from_orm", return_value=mock_user_schema) as mock_from_orm:
            result = await get_current_user_info(mock_user)

            assert mock_from_orm.called


@pytest.mark.unit
class TestDebugCheckRefreshTokenEndpoint:
    """Test /auth/debug/check-refresh-token endpoint."""

    @pytest.mark.asyncio
    async def test_debug_endpoint_rejects_in_production(self):
        """Should return 404 when DEBUG is False."""
        from app.api.v1.auth import debug_check_refresh_token

        mock_data = Mock()
        mock_user = Mock(spec=User)
        mock_db = AsyncMock()

        with patch("app.api.v1.auth.settings.DEBUG", False):
            with pytest.raises(HTTPException) as exc_info:
                await debug_check_refresh_token(mock_data, mock_user, mock_db)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_debug_endpoint_returns_token_info(self):
        """Should return detailed token info in DEBUG mode."""
        from app.api.v1.auth import debug_check_refresh_token

        mock_data = Mock()
        mock_data.refresh_token = "token"
        mock_user = Mock(spec=User)
        mock_db = AsyncMock()

        user_id = uuid4()
        mock_payload = {
            "jti": "jti123456789",
            "type": "refresh",
            "sub": str(user_id),
            "exp": 1234567890,
        }

        mock_token = Mock()
        mock_token.is_expired = False
        mock_token.is_revoked = False
        mock_token.expires_at = datetime.now()

        with patch("app.api.v1.auth.settings.DEBUG", True):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with patch("app.api.v1.auth.refresh_token_crud.get_by_token_hash", new=AsyncMock(return_value=mock_token)):
                    result = await debug_check_refresh_token(mock_data, mock_user, mock_db)

                    assert result["decode_success"] is True
                    assert result["in_database"] is True
                    assert result["payload"]["type"] == "refresh"

    @pytest.mark.asyncio
    async def test_debug_endpoint_handles_invalid_token(self):
        """Should return error info for invalid tokens."""
        from app.api.v1.auth import debug_check_refresh_token

        mock_data = Mock()
        mock_data.refresh_token = "invalid_token"
        mock_user = Mock(spec=User)
        mock_db = AsyncMock()

        with patch("app.api.v1.auth.settings.DEBUG", True):
            with patch("app.api.v1.auth.decode_token", side_effect=ValueError("Invalid")):
                result = await debug_check_refresh_token(mock_data, mock_user, mock_db)

                assert result["decode_success"] is False
                assert "error" in result

    @pytest.mark.asyncio
    async def test_debug_endpoint_shows_not_in_database(self):
        """Should show when token is not in database."""
        from app.api.v1.auth import debug_check_refresh_token

        mock_data = Mock()
        mock_data.refresh_token = "token"
        mock_user = Mock(spec=User)
        mock_db = AsyncMock()

        mock_payload = {
            "jti": "jti123",
            "type": "refresh",
            "sub": str(uuid4()),
            "exp": 1234567890,
        }

        with patch("app.api.v1.auth.settings.DEBUG", True):
            with patch("app.api.v1.auth.decode_token", return_value=mock_payload):
                with patch("app.api.v1.auth.refresh_token_crud.get_by_token_hash", new=AsyncMock(return_value=None)):
                    result = await debug_check_refresh_token(mock_data, mock_user, mock_db)

                    assert result["decode_success"] is True
                    assert result["in_database"] is False
