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
