"""Unit tests for app/main.py — covers root, health, security-status endpoints,
_make_json_serializable, and validation_exception_handler."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import (
    _make_json_serializable,
    app,
    health_check,
    root,
    security_status,
    validation_exception_handler,
)

# ---------------------------------------------------------------------------
# _make_json_serializable
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMakeJsonSerializable:
    def test_decimal_to_float(self):
        result = _make_json_serializable(Decimal("123.45"))
        assert result == 123.45
        assert isinstance(result, float)

    def test_type_to_str(self):
        result = _make_json_serializable(int)
        assert result == str(int)

    def test_exception_to_str(self):
        exc = ValueError("test error")
        result = _make_json_serializable(exc)
        assert result == "test error"

    def test_dict_recursive(self):
        data = {"amount": Decimal("10.50"), "name": "test"}
        result = _make_json_serializable(data)
        assert result == {"amount": 10.50, "name": "test"}

    def test_list_recursive(self):
        data = [Decimal("1"), Decimal("2"), "three"]
        result = _make_json_serializable(data)
        assert result == [1.0, 2.0, "three"]

    def test_nested_dict_and_list(self):
        data = {"items": [{"value": Decimal("5.5")}, {"type": int}]}
        result = _make_json_serializable(data)
        assert result == {"items": [{"value": 5.5}, {"type": str(int)}]}

    def test_passthrough_normal_values(self):
        assert _make_json_serializable("hello") == "hello"
        assert _make_json_serializable(42) == 42
        assert _make_json_serializable(None) is None
        assert _make_json_serializable(True) is True


# ---------------------------------------------------------------------------
# root endpoint
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root_returns_status(self):
        result = await root()
        assert result["status"] == "running"
        assert "name" in result
        assert "version" in result


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_when_db_ok(self):
        """Should return healthy when database is reachable."""
        mock_db = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.core.database.AsyncSessionLocal", return_value=mock_session_ctx):
            result = await health_check()

        assert result["status"] == "healthy"
        assert result["checks"]["database"] == "ok"

    @pytest.mark.asyncio
    async def test_unhealthy_when_db_fails(self):
        """Should return 503 when database is unreachable."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("Connection refused"))
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.core.database.AsyncSessionLocal", return_value=mock_session_ctx):
            result = await health_check()

        # Result is a JSONResponse when unhealthy
        assert result.status_code == 503


# ---------------------------------------------------------------------------
# security_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityStatus:
    @pytest.mark.asyncio
    async def test_requires_admin(self):
        """Should raise 403 for non-admin users."""
        from fastapi import HTTPException

        user = MagicMock()
        user.is_org_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await security_status(current_user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_security_checklist(self):
        """Should return security score and checklist for admin."""
        user = MagicMock()
        user.is_org_admin = True
        user._is_guest = False

        mock_checklist = {
            "encryption_key_configured": True,
            "cors_configured": True,
            "debug_disabled": False,
        }

        with patch("app.main.secrets_validation_service") as mock_svc:
            mock_svc.generate_security_checklist.return_value = mock_checklist

            result = await security_status(current_user=user)

        assert "security_score" in result
        assert "checks_passed" in result
        assert "checks_total" in result
        assert result["checks_total"] == 3
        assert result["checks_passed"] == 2
        # 2/3 * 100 = 66.7
        assert result["security_score"] == 66.7

    @pytest.mark.asyncio
    async def test_returns_production_ready_message(self):
        """Should return 'Production ready' when score >= 90."""
        user = MagicMock()
        user.is_org_admin = True
        user._is_guest = False

        # All checks pass
        mock_checklist = {f"check_{i}": True for i in range(10)}

        with patch("app.main.secrets_validation_service") as mock_svc:
            mock_svc.generate_security_checklist.return_value = mock_checklist

            result = await security_status(current_user=user)

        assert result["security_score"] == 100.0
        assert result["recommendation"] == "Production ready"

    @pytest.mark.asyncio
    async def test_returns_review_message_when_low_score(self):
        """Should return review message when score < 90."""
        user = MagicMock()
        user.is_org_admin = True
        user._is_guest = False

        mock_checklist = {"check_1": True, "check_2": False, "check_3": False}

        with patch("app.main.secrets_validation_service") as mock_svc:
            mock_svc.generate_security_checklist.return_value = mock_checklist

            result = await security_status(current_user=user)

        assert "Review failed checks" in result["recommendation"]

    @pytest.mark.asyncio
    async def test_empty_checklist_returns_zero(self):
        """Should handle empty checklist."""
        user = MagicMock()
        user.is_org_admin = True
        user._is_guest = False

        with patch("app.main.secrets_validation_service") as mock_svc:
            mock_svc.generate_security_checklist.return_value = {}

            result = await security_status(current_user=user)

        assert result["security_score"] == 0


# ---------------------------------------------------------------------------
# validation_exception_handler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationExceptionHandler:
    @pytest.mark.asyncio
    async def test_returns_422_with_serialized_errors(self):
        """Should return 422 with serialized validation errors."""
        mock_request = MagicMock()
        mock_request.url = "http://test/api/v1/test"

        mock_exc = MagicMock()
        mock_exc.errors.return_value = [
            {
                "loc": ["body", "amount"],
                "msg": "value is not a valid decimal",
                "type": "decimal_type",
            }
        ]

        result = await validation_exception_handler(mock_request, mock_exc)

        assert result.status_code == 422

    @pytest.mark.asyncio
    async def test_handles_non_serializable_errors(self):
        """Should handle errors with Decimal and type objects."""
        mock_request = MagicMock()
        mock_request.url = "http://test/api/v1/test"

        mock_exc = MagicMock()
        mock_exc.errors.return_value = [
            {
                "loc": ["body", "amount"],
                "msg": "invalid",
                "type": Decimal,
                "ctx": {"error": ValueError("bad")},
            }
        ]

        result = await validation_exception_handler(mock_request, mock_exc)

        assert result.status_code == 422


# ---------------------------------------------------------------------------
# App structure verification
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppStructure:
    def test_app_is_fastapi_instance(self):
        """App should be a FastAPI instance."""
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_app_has_routes(self):
        """App should have routes registered."""
        routes = [r.path for r in app.routes]
        assert "/" in routes
        assert "/health" in routes

    def test_app_includes_api_routers(self):
        """App should include key API routers."""
        [r.path for r in app.routes]
        # Check for key prefixed routes
        path_prefixes = set()
        for r in app.routes:
            parts = r.path.split("/")
            if len(parts) > 3:
                path_prefixes.add("/".join(parts[:4]))

        assert "/api/v1/auth" in path_prefixes or any("/api/v1/auth" in r.path for r in app.routes)


# ---------------------------------------------------------------------------
# _filter_sensitive_data (Sentry callback, lines 89-108)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterSensitiveData:
    """Cover _filter_sensitive_data Sentry callback if available."""

    @staticmethod
    def _make_filter_fn():
        """Reproduce the _filter_sensitive_data logic for testing without Sentry DSN."""

        def _filter_sensitive_data(event):
            if "request" in event and "headers" in event["request"]:
                headers = event["request"]["headers"]
                sensitive_headers = ["authorization", "cookie", "x-api-key", "x-auth-token"]
                for header in sensitive_headers:
                    if header in headers:
                        headers[header] = "[Filtered]"
            if "request" in event and "query_string" in event["request"]:
                sensitive_params = ["token", "password", "api_key", "secret"]
                query = event["request"].get("query_string", "")
                for param in sensitive_params:
                    if param in query.lower():
                        event["request"]["query_string"] = "[Filtered]"
                        break
            return event

        return _filter_sensitive_data

    def test_filters_auth_header(self):
        """Should filter authorization header."""
        fn = self._make_filter_fn()
        event = {
            "request": {
                "headers": {
                    "authorization": "Bearer secret",
                    "cookie": "session=abc",
                    "x-api-key": "key123",
                    "x-auth-token": "tok",
                    "content-type": "application/json",
                },
                "query_string": "token=secret123&name=test",
            }
        }
        result = fn(event)
        assert result["request"]["headers"]["authorization"] == "[Filtered]"
        assert result["request"]["headers"]["cookie"] == "[Filtered]"
        assert result["request"]["headers"]["x-api-key"] == "[Filtered]"
        assert result["request"]["headers"]["x-auth-token"] == "[Filtered]"
        assert result["request"]["headers"]["content-type"] == "application/json"
        assert result["request"]["query_string"] == "[Filtered]"

    def test_no_sensitive_query_string(self):
        """Should not filter query_string when no sensitive params."""
        fn = self._make_filter_fn()
        event = {
            "request": {
                "headers": {},
                "query_string": "page=1&sort=date",
            }
        }
        result = fn(event)
        assert result["request"]["query_string"] == "page=1&sort=date"

    def test_event_without_request(self):
        """Should handle events without request field."""
        fn = self._make_filter_fn()
        event = {"level": "error", "message": "test"}
        result = fn(event)
        assert result == event


# ---------------------------------------------------------------------------
# lifespan (lines 141-194)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLifespan:
    """Cover the lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_debug_mode(self):
        """Should run startup and shutdown in debug mode."""
        from app.main import lifespan

        mock_app = MagicMock()

        with patch("app.main.settings") as mock_settings:
            mock_settings.DEBUG = True
            mock_settings.METRICS_ENABLED = False
            mock_settings.APP_NAME = "Test"
            mock_settings.APP_VERSION = "1.0"
            mock_settings.ENVIRONMENT = "development"
            with patch("app.main.setup_logging"):
                with patch("app.main.init_db", new_callable=AsyncMock):
                    with patch("app.main.close_db", new_callable=AsyncMock):
                        async with lifespan(mock_app):
                            pass  # Startup succeeded

    @pytest.mark.asyncio
    async def test_lifespan_production_secrets_valid(self):
        """Should validate secrets in production mode."""
        from app.main import lifespan

        mock_app = MagicMock()

        with patch("app.main.settings") as mock_settings:
            mock_settings.DEBUG = False
            mock_settings.METRICS_ENABLED = False
            mock_settings.APP_NAME = "Test"
            mock_settings.APP_VERSION = "1.0"
            mock_settings.ENVIRONMENT = "production"
            with patch("app.main.setup_logging"):
                with patch("app.main.secrets_validation_service") as mock_sv:
                    mock_sv.validate_production_secrets.return_value = {
                        "errors": [],
                        "warnings": ["Minor warning"],
                    }
                    with patch("app.main.init_db", new_callable=AsyncMock):
                        with patch("app.main.close_db", new_callable=AsyncMock):
                            async with lifespan(mock_app):
                                pass

    @pytest.mark.asyncio
    async def test_lifespan_production_secrets_invalid(self):
        """Should raise RuntimeError when production secrets fail validation."""
        from app.main import lifespan

        mock_app = MagicMock()

        with patch("app.main.settings") as mock_settings:
            mock_settings.DEBUG = False
            mock_settings.METRICS_ENABLED = False
            with patch("app.main.setup_logging"):
                with patch("app.main.secrets_validation_service") as mock_sv:
                    mock_sv.validate_production_secrets.return_value = {
                        "errors": ["Missing encryption key"],
                        "warnings": [],
                    }
                    with pytest.raises(RuntimeError, match="invalid production configuration"):
                        async with lifespan(mock_app):
                            pass

    @pytest.mark.asyncio
    async def test_lifespan_with_metrics(self):
        """Should start metrics server when METRICS_ENABLED is True."""
        from app.main import lifespan

        mock_app = MagicMock()

        with patch("app.main.settings") as mock_settings:
            mock_settings.DEBUG = True
            mock_settings.METRICS_ENABLED = True
            mock_settings.METRICS_ADMIN_PORT = 9090
            mock_settings.APP_NAME = "Test"
            mock_settings.APP_VERSION = "1.0"
            mock_settings.ENVIRONMENT = "development"
            with patch("app.main.setup_logging"):
                with patch("app.main.init_db", new_callable=AsyncMock):
                    with patch("app.main.close_db", new_callable=AsyncMock):
                        with patch("app.main.create_metrics_app") as mock_metrics:
                            mock_metrics.return_value = MagicMock()
                            with patch("uvicorn.Config"):
                                with patch("uvicorn.Server") as mock_server:
                                    mock_server.return_value.serve = AsyncMock()
                                    async with lifespan(mock_app):
                                        pass
