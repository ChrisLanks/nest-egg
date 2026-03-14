"""Unit tests for PasswordValidationService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.password_validation_service import PasswordValidationService


class TestValidatePasswordStrength:
    """Tests for validate_password_strength static method."""

    def test_valid_strong_password(self):
        is_valid, errors = PasswordValidationService.validate_password_strength(
            "MyStr0ng!Pass_word"
        )
        assert is_valid is True
        assert errors == []

    def test_too_short(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("Abc1!xyz")
        assert is_valid is False
        assert any("12 characters" in e for e in errors)

    def test_missing_uppercase(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("mystr0ng!password")
        assert is_valid is False
        assert any("uppercase" in e for e in errors)

    def test_missing_lowercase(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("MYSTR0NG!PASSWORD")
        assert is_valid is False
        assert any("lowercase" in e for e in errors)

    def test_missing_digit(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("MyStrong!Password")
        assert is_valid is False
        assert any("digit" in e for e in errors)

    def test_missing_special_character(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("MyStr0ngPassword")
        assert is_valid is False
        assert any("special character" in e for e in errors)

    def test_common_password(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("password")
        assert is_valid is False
        assert any("common" in e.lower() for e in errors)

    def test_common_password_case_insensitive(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("PASSWORD")
        assert is_valid is False
        assert any("common" in e.lower() for e in errors)

    def test_sequential_characters(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("My1234Pass!word!")
        assert is_valid is False
        assert any("sequential" in e for e in errors)

    def test_sequential_alpha_characters(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("Myabcde1Pass!word")
        assert is_valid is False
        assert any("sequential" in e for e in errors)

    def test_repeated_characters(self):
        is_valid, errors = PasswordValidationService.validate_password_strength("Myaaaaaaa1Pass!")
        assert is_valid is False
        assert any("repeated" in e for e in errors)

    def test_multiple_errors(self):
        """Short, no uppercase, no digit, no special."""
        is_valid, errors = PasswordValidationService.validate_password_strength("short")
        assert is_valid is False
        assert len(errors) >= 3


class TestCheckPasswordBreach:
    """Tests for check_password_breach async method."""

    @pytest.mark.asyncio
    async def test_password_found_in_breach(self):
        """Should detect breached password."""
        import hashlib

        password = "testpassword"  # pragma: allowlist secret
        sha1 = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
        suffix = sha1[5:]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = f"{suffix}:42\nOTHERSUFFIX:10\n"

        with patch("app.services.password_validation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            is_breached, count = await PasswordValidationService.check_password_breach(password)

        assert is_breached is True
        assert count == 42

    @pytest.mark.asyncio
    async def test_password_not_in_breach(self):
        """Should not flag clean password."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "AAAAAAA:5\nBBBBBBB:10\n"

        with patch("app.services.password_validation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            is_breached, count = await PasswordValidationService.check_password_breach(
                "UniqueSuperStr0ng!Pass"
            )

        assert is_breached is False
        assert count is None

    @pytest.mark.asyncio
    async def test_api_error_returns_false(self):
        """Should fail open on API errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.services.password_validation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            is_breached, count = await PasswordValidationService.check_password_breach("anything")

        assert is_breached is False
        assert count is None

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self):
        """Should fail open on timeout."""
        import httpx

        with patch("app.services.password_validation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            is_breached, count = await PasswordValidationService.check_password_breach("anything")

        assert is_breached is False
        assert count is None

    @pytest.mark.asyncio
    async def test_generic_exception_returns_false(self):
        """Should fail open on any exception."""
        with patch("app.services.password_validation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("unexpected"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            is_breached, count = await PasswordValidationService.check_password_breach("anything")

        assert is_breached is False
        assert count is None


class TestValidateAndRaiseAsync:
    """Tests for validate_and_raise_async method."""

    @pytest.mark.asyncio
    async def test_valid_password_no_breach_passes(self):
        """Should not raise for valid, non-breached password."""
        with patch.object(
            PasswordValidationService,
            "check_password_breach",
            new=AsyncMock(return_value=(False, None)),
        ):
            await PasswordValidationService.validate_and_raise_async("MyStr0ng!Pass_word")

    @pytest.mark.asyncio
    async def test_invalid_password_raises_400(self):
        """Should raise HTTPException for weak password."""
        with pytest.raises(HTTPException) as exc_info:
            await PasswordValidationService.validate_and_raise_async("weak", check_breach=False)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_breached_password_raises_400(self):
        """Should raise HTTPException for breached password."""
        with patch.object(
            PasswordValidationService,
            "check_password_breach",
            new=AsyncMock(return_value=(True, 1000)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await PasswordValidationService.validate_and_raise_async("MyStr0ng!Pass_word")
            assert exc_info.value.status_code == 400
            assert any("breach" in e.lower() for e in exc_info.value.detail["errors"])

    @pytest.mark.asyncio
    async def test_skip_breach_check(self):
        """Should skip breach check when check_breach=False."""
        with patch.object(
            PasswordValidationService,
            "check_password_breach",
            new=AsyncMock(return_value=(False, None)),
        ) as mock_check:
            await PasswordValidationService.validate_and_raise_async(
                "MyStr0ng!Pass_word", check_breach=False
            )
            mock_check.assert_not_called()


class TestValidateAndRaise:
    """Tests for synchronous validate_and_raise method."""

    def test_valid_password_passes(self):
        PasswordValidationService.validate_and_raise("MyStr0ng!Pass_word")

    def test_invalid_password_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            PasswordValidationService.validate_and_raise("weak")
        assert exc_info.value.status_code == 400
        assert "errors" in exc_info.value.detail
