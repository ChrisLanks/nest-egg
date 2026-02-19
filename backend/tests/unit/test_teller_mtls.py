"""Tests for Teller mTLS certificate handling in _make_request."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.teller_service import TellerService


class TestTellerMtls:
    """Verify that _make_request passes the mTLS certificate correctly."""

    @pytest.mark.asyncio
    async def test_cert_passed_to_httpx_when_configured(self):
        """Should pass TELLER_CERT_PATH as cert to httpx.AsyncClient."""
        service = TellerService()

        mock_response = MagicMock()
        mock_response.content = b'{"id": "acc_1"}'
        mock_response.json.return_value = {"id": "acc_1"}
        mock_response.raise_for_status = MagicMock()

        captured_cert = []

        original_init = httpx.AsyncClient.__init__

        def capturing_init(self_client, **kwargs):
            captured_cert.append(kwargs.get("cert"))
            # Minimal init so request() works via mock
            original_init(self_client, **kwargs)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_CERT_PATH = "/path/to/teller_cert.pem"
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key_abc"
            mock_settings.TELLER_ENV = "production"

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)

                await service._make_request("GET", "/accounts", access_token="tok_abc")

                # httpx.AsyncClient must be instantiated with the cert path
                mock_client_cls.assert_called_once_with(cert="/path/to/teller_cert.pem")

    @pytest.mark.asyncio
    async def test_cert_is_none_when_not_configured(self):
        """Should pass cert=None when TELLER_CERT_PATH is empty string."""
        service = TellerService()

        mock_response = MagicMock()
        mock_response.content = b"{}"
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_CERT_PATH = ""
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key_abc"
            mock_settings.TELLER_ENV = "sandbox"

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)

                await service._make_request("GET", "/accounts")

                mock_client_cls.assert_called_once_with(cert=None)

    @pytest.mark.asyncio
    async def test_access_token_used_as_basic_auth_username(self):
        """Should send access token as Basic Auth username with empty password."""
        service = TellerService()

        mock_response = MagicMock()
        mock_response.content = b"[]"
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_CERT_PATH = "/cert.pem"
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key_abc"
            mock_settings.TELLER_ENV = "production"

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)

                access_token = "test_enrollment_token"
                await service._make_request("GET", "/accounts", access_token=access_token)

                call_kwargs = mock_client.request.call_args
                assert call_kwargs.kwargs["auth"] == (access_token, "")

    @pytest.mark.asyncio
    async def test_api_key_used_as_fallback_when_no_access_token(self):
        """Should fall back to API key when access_token is not provided."""
        service = TellerService()

        mock_response = MagicMock()
        mock_response.content = b"{}"
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_CERT_PATH = ""
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "live_key_abc"
            mock_settings.TELLER_ENV = "production"

            # Patch service's api_key (set during __init__ before our settings patch)
            service.api_key = "live_key_abc"

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)

                await service._make_request("GET", "/enrollments/enr_1")

                call_kwargs = mock_client.request.call_args
                assert call_kwargs.kwargs["auth"] == ("live_key_abc", "")

    @pytest.mark.asyncio
    async def test_cert_and_access_token_used_together(self):
        """Should use both mTLS cert AND access token Basic Auth simultaneously."""
        service = TellerService()

        mock_response = MagicMock()
        mock_response.content = b'[{"id": "txn_1"}]'
        mock_response.json.return_value = [{"id": "txn_1"}]
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_CERT_PATH = "/certs/teller.pem"
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key_abc"
            mock_settings.TELLER_ENV = "production"

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)

                await service._make_request(
                    "GET",
                    "/accounts/acc_1/transactions",
                    access_token="enr_token_xyz",
                )

                # Client created with cert
                mock_client_cls.assert_called_once_with(cert="/certs/teller.pem")

                # Request sent with access token as Basic Auth
                call_kwargs = mock_client.request.call_args
                assert call_kwargs.kwargs["auth"] == ("enr_token_xyz", "")

    @pytest.mark.asyncio
    async def test_correct_url_and_method_passed(self):
        """Should construct the correct URL from base_url + path."""
        service = TellerService()
        service.base_url = "https://api.teller.io"

        mock_response = MagicMock()
        mock_response.content = b"{}"
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_CERT_PATH = ""
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"
            mock_settings.TELLER_ENV = "production"

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)

                await service._make_request("GET", "/accounts/acc_abc/transactions")

                call_kwargs = mock_client.request.call_args
                assert call_kwargs.kwargs["method"] == "GET"
                assert call_kwargs.kwargs["url"] == "https://api.teller.io/accounts/acc_abc/transactions"

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_dict(self):
        """Should return {} when response body is empty."""
        service = TellerService()

        mock_response = MagicMock()
        mock_response.content = b""  # Empty body
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_CERT_PATH = ""
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"
            mock_settings.TELLER_ENV = "sandbox"

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)

                result = await service._make_request("DELETE", "/enrollments/enr_1")

                assert result == {}
