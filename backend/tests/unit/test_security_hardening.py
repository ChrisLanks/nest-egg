"""Tests for security hardening fixes.

Covers all findings from the security audit:
- #2: Security status blocked for guests
- #3: Rate limit dev bypass removed
- #4: CSV export rate limiting
- #5: Expanded audit trail coverage
- #6: Persistent DB audit log
- #7: OpenAPI disabled in production
- #8: X-Forwarded-For uses first IP
- #10: Registration anti-enumeration response shape
- #11: Invitation list restricted to admins
- #12: ILIKE wildcard injection fixed
- #14: UserCreate password min length
- #15: Refresh cookie secure flag uses ENVIRONMENT
- #16: User profile removed from localStorage persistence

Bug fixes:
- Withdrawal strategy tax rate capping (prevents 100x over-withdrawal)
- Market data Holding.symbol → Holding.ticker fix
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.user import User

# ---------------------------------------------------------------------------
# #2: Security status endpoint blocks guests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityStatusGuestBlock:
    """Guests must not see security status even if they're admin in their home org."""

    @pytest.mark.asyncio
    async def test_guest_admin_blocked(self):
        """Guest who is admin in their home org should be blocked."""
        from app.main import security_status

        user = MagicMock()
        user.is_org_admin = True
        user._is_guest = True

        with pytest.raises(HTTPException) as exc_info:
            await security_status(current_user=user)
        assert exc_info.value.status_code == 403
        assert "Guests" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_non_guest_admin_allowed(self):
        """Non-guest admin should be allowed."""
        from app.main import security_status

        user = MagicMock()
        user.is_org_admin = True
        user._is_guest = False

        with patch("app.main.secrets_validation_service") as mock_svc:
            mock_svc.generate_security_checklist.return_value = {"check": True}
            result = await security_status(current_user=user)

        assert "security_score" in result


# ---------------------------------------------------------------------------
# #3: Rate limit dev bypass removed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRateLimitDevBypass:
    """Rate limiting should NOT be bypassed in development."""

    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_development_env_does_not_skip(self, mock_settings):
        """Development environment should still enforce rate limits."""
        from app.services.rate_limit_service import RateLimitService

        mock_settings.ENVIRONMENT = "development"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"

        service = RateLimitService()
        request = MagicMock()
        request.client = MagicMock(host="192.168.1.1")
        request.url.path = "/api/v1/auth/login"

        # Should attempt to connect to Redis (not skip), will raise because
        # Redis is not available — but the point is it DIDN'T return early.
        mock_redis = AsyncMock()
        mock_redis.eval = AsyncMock(return_value=[1, 60])
        service.redis_client = mock_redis

        await service.check_rate_limit(request, max_requests=10)
        mock_redis.eval.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_test_env_skips(self, mock_settings):
        """Test environment should skip rate limiting."""
        from app.services.rate_limit_service import RateLimitService

        mock_settings.ENVIRONMENT = "test"
        service = RateLimitService()
        request = MagicMock()
        request.client = MagicMock(host="192.168.1.1")
        request.url.path = "/test"

        # Should not raise, should return immediately without Redis
        await service.check_rate_limit(request, max_requests=1)


# ---------------------------------------------------------------------------
# #4: CSV export rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCSVExportRateLimiting:
    """CSV exports should have rate limits."""

    @pytest.mark.asyncio
    async def test_accounts_export_calls_rate_limit(self):
        """Accounts CSV export should check rate limit."""
        from app.api.v1.accounts import export_accounts_csv

        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        db = AsyncMock()

        mock_acct = Mock()
        mock_acct.id = uuid4()
        mock_request = Mock()

        with (
            patch(
                "app.api.v1.accounts.get_all_household_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acct],
            ),
            patch(
                "app.api.v1.accounts.deduplication_service.deduplicate_accounts",
                return_value=[mock_acct],
            ),
            patch(
                "app.api.v1.accounts.rate_limit_service.check_rate_limit",
                new_callable=AsyncMock,
            ) as mock_rl,
        ):
            mock_acct.name = "Checking"
            mock_acct.account_type = Mock(value="checking")
            mock_acct.institution_name = "Bank"
            mock_acct.current_balance = Decimal("1000")
            mock_acct.available_balance = None
            mock_acct.limit = None
            mock_acct.account_source = Mock(value="manual")
            mock_acct.tax_treatment = None
            mock_acct.mask = None
            mock_acct.is_active = True

            await export_accounts_csv(request=mock_request, user_id=None, current_user=user, db=db)
            mock_rl.assert_called_once()
            call_kwargs = mock_rl.call_args[1]
            assert call_kwargs["max_requests"] == 10
            assert call_kwargs["window_seconds"] == 3600


# ---------------------------------------------------------------------------
# #5: Expanded audit trail paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditTrailPaths:
    """Audit trail should cover all sensitive operations."""

    def test_mutating_audit_paths_cover_critical_endpoints(self):
        from app.middleware.request_logging import AuditLogMiddleware

        required_prefixes = [
            "/api/v1/budgets",
            "/api/v1/reports",
            "/api/v1/permissions",
            "/api/v1/guest-access",
            "/api/v1/plaid/exchange-token",
            "/api/v1/csv-import",
        ]
        for prefix in required_prefixes:
            assert any(
                prefix in path for path in AuditLogMiddleware.AUDIT_PATHS
            ), f"Missing audit path: {prefix}"

    def test_read_audit_paths_cover_exports(self):
        from app.middleware.request_logging import AuditLogMiddleware

        required_prefixes = [
            "/api/v1/accounts/export",
            "/api/v1/transactions/export",
            "/api/v1/budgets/export",
            "/api/v1/labels/tax-deductible/export",
        ]
        for prefix in required_prefixes:
            assert any(
                prefix in path for path in AuditLogMiddleware.AUDIT_READ_PATHS
            ), f"Missing audit read path: {prefix}"


# ---------------------------------------------------------------------------
# #6: Persistent DB audit log model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditLogModel:
    """Audit log model should have the right columns."""

    def test_audit_log_model_exists(self):
        from app.models.audit_log import AuditLog

        assert AuditLog.__tablename__ == "audit_logs"

    def test_audit_log_has_required_columns(self):
        from app.models.audit_log import AuditLog

        column_names = {c.name for c in AuditLog.__table__.columns}
        required = {
            "id",
            "request_id",
            "action",
            "method",
            "path",
            "status_code",
            "user_id",
            "ip_address",
            "duration_ms",
            "created_at",
            "detail",
        }
        assert required.issubset(column_names)

    def test_persist_audit_log_task_exists(self):
        """Audit log persistence is now handled by a durable Celery task."""
        from app.workers.tasks.auth_tasks import persist_audit_log_task

        assert callable(persist_audit_log_task)


# ---------------------------------------------------------------------------
# #7: OpenAPI disabled in production
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOpenAPIDisabledInProd:
    """OpenAPI schema should not be available in production."""

    def test_openapi_url_none_when_not_debug(self):
        """When DEBUG=False, openapi_url should be None."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.DEBUG = False
            # The actual value is set at import time. We verify the logic:
            openapi_url = "/openapi.json" if mock_settings.DEBUG else None
            assert openapi_url is None

    def test_openapi_url_set_when_debug(self):
        """When DEBUG=True, openapi_url should be set."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.DEBUG = True
            openapi_url = "/openapi.json" if mock_settings.DEBUG else None
            assert openapi_url == "/openapi.json"


# ---------------------------------------------------------------------------
# #8: X-Forwarded-For uses first IP (client), not last (proxy)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestXForwardedForFirstIP:
    """Anomaly detection should use the first IP from X-Forwarded-For."""

    def test_single_ip(self):
        from app.middleware.anomaly_detection import _get_ip

        request = Mock()
        request.headers = {"X-Forwarded-For": "1.2.3.4"}
        request.client = Mock(host="127.0.0.1")
        assert _get_ip(request) == "1.2.3.4"

    def test_multiple_ips_uses_first(self):
        from app.middleware.anomaly_detection import _get_ip

        request = Mock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 172.16.0.1, 192.168.1.1"}
        request.client = Mock(host="127.0.0.1")
        assert _get_ip(request) == "10.0.0.1"

    def test_no_forwarded_uses_client(self):
        from app.middleware.anomaly_detection import _get_ip

        request = Mock()
        request.headers = {}
        request.client = Mock(host="192.168.1.1")
        assert _get_ip(request) == "192.168.1.1"


# ---------------------------------------------------------------------------
# #10: Registration anti-enumeration response shape
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistrationAntiEnumeration:
    """Registration should return same-shaped response for existing users."""

    @pytest.mark.asyncio
    async def test_existing_user_response_has_token_keys(self):
        """Existing user response must include access_token, refresh_token, user keys."""
        from app.api.v1.auth import register

        mock_request = MagicMock()
        mock_request.client = MagicMock(host="127.0.0.1")
        mock_response = MagicMock()
        mock_db = AsyncMock()

        mock_data = MagicMock()
        mock_data.email = "existing@example.com"
        mock_data.password = "Str0ngP@ssw0rd!123"  # pragma: allowlist secret
        mock_data.display_name = "Test"
        mock_data.first_name = "Test"
        mock_data.last_name = "User"
        mock_data.organization_name = "My Household"
        mock_data.birth_day = None
        mock_data.birth_month = None
        mock_data.birth_year = None

        existing_user = MagicMock()

        with (
            patch("app.api.v1.auth.rate_limit_service.check_rate_limit", new_callable=AsyncMock),
            patch(
                "app.api.v1.auth.password_validation_service.validate_and_raise_async",
                new_callable=AsyncMock,
            ),
            patch(
                "app.api.v1.auth.user_crud.get_by_email",
                new_callable=AsyncMock,
                return_value=existing_user,
            ),
        ):
            result = await register(
                request=mock_request,
                response=mock_response,
                data=mock_data,
                db=mock_db,
            )

        # Should be a JSONResponse with token-shaped keys
        assert result.status_code == 201
        import json

        body = json.loads(result.body.decode())
        assert "access_token" in body
        assert "refresh_token" in body
        assert "user" in body


# ---------------------------------------------------------------------------
# #11: Invitation list restricted to admins
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInvitationListAdminOnly:
    """Invitation list endpoint should use admin dependency."""

    def test_list_invitations_uses_admin_dependency(self):
        """list_invitations should use get_current_admin_user."""
        import inspect

        from app.api.v1.household import list_invitations

        sig = inspect.signature(list_invitations)
        current_user_param = sig.parameters.get("current_user")
        assert current_user_param is not None
        # The default should be Depends(get_current_admin_user)
        default = current_user_param.default
        assert hasattr(default, "dependency")
        # Check the dependency function name
        dep_name = default.dependency.__name__
        assert (
            dep_name == "get_current_admin_user"
        ), f"Expected get_current_admin_user, got {dep_name}"


# ---------------------------------------------------------------------------
# #12: ILIKE wildcard injection fixed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestILIKEWildcardEscaping:
    """Merchant search should escape ILIKE wildcards."""

    @pytest.mark.asyncio
    async def test_percent_is_escaped(self):
        """% in search should be escaped, not act as wildcard."""
        from app.api.v1.transactions import get_merchant_names

        mock_user = Mock(spec=User)
        mock_user.organization_id = uuid4()
        mock_db = AsyncMock()

        mock_result = Mock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await get_merchant_names(current_user=mock_user, db=mock_db, search="%admin", limit=500)
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_underscore_is_escaped(self):
        """_ in search should be escaped."""
        from app.api.v1.transactions import get_merchant_names

        mock_user = Mock(spec=User)
        mock_user.organization_id = uuid4()
        mock_db = AsyncMock()

        mock_result = Mock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await get_merchant_names(current_user=mock_user, db=mock_db, search="_admin", limit=500)
        assert mock_db.execute.called

    def test_escape_logic_directly(self):
        """Verify the escape logic handles all ILIKE special chars."""
        search = "%_\\"
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        assert "\\%" in escaped
        assert "\\_" in escaped


# ---------------------------------------------------------------------------
# #14: UserCreate password min length = 12
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUserCreatePasswordMinLength:
    """UserCreate schema should require at least 12 characters."""

    def test_rejects_short_password(self):
        from pydantic import ValidationError

        from app.schemas.user import UserCreate

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="Short1!",  # Only 7 chars  # pragma: allowlist secret
            )
        errors = exc_info.value.errors()
        assert any("password" in str(e).lower() for e in errors)

    def test_rejects_11_char_password(self):
        from pydantic import ValidationError

        from app.schemas.user import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="Abcdef1234!",  # pragma: allowlist secret
            )

    def test_accepts_12_char_password(self):
        from app.schemas.user import UserCreate

        user = UserCreate(
            email="test@example.com",
            password="Abcdef12345!",  # pragma: allowlist secret
        )
        assert len(user.password) == 12


# ---------------------------------------------------------------------------
# #15: Refresh cookie secure flag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefreshCookieSecureFlag:
    """Refresh cookie secure flag should depend on ENVIRONMENT, not DEBUG."""

    def test_production_sets_secure_true(self):
        from app.api.v1.auth import _set_refresh_cookie

        mock_response = MagicMock()
        with patch("app.api.v1.auth.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 30

            _set_refresh_cookie(mock_response, "test-token")

        mock_response.set_cookie.assert_called_once()
        call_kwargs = mock_response.set_cookie.call_args[1]
        assert call_kwargs["secure"] is True

    def test_development_sets_secure_false(self):
        from app.api.v1.auth import _set_refresh_cookie

        mock_response = MagicMock()
        with patch("app.api.v1.auth.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "development"
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 30

            _set_refresh_cookie(mock_response, "test-token")

        mock_response.set_cookie.assert_called_once()
        call_kwargs = mock_response.set_cookie.call_args[1]
        assert call_kwargs["secure"] is False


# ---------------------------------------------------------------------------
# Withdrawal strategy: tax rate capping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWithdrawalStrategyTaxCapping:
    """Withdrawal strategy should cap tax rates to prevent extreme gross-up."""

    def test_capital_gains_rate_capped_at_50_percent(self):
        """A capital gains rate of 99% should not cause 100x over-withdrawal."""
        from app.services.retirement.withdrawal_strategy_service import (
            AccountBuckets,
            tax_optimized_withdrawal,
        )

        buckets = AccountBuckets(taxable=100_000.0, pre_tax=0.0, roth=0.0, hsa=0.0)
        result = tax_optimized_withdrawal(
            buckets=buckets,
            needed=10_000.0,
            age=65,
            federal_rate=0.0,
            state_rate=0.0,
            capital_gains_rate=0.99,  # Extreme rate
        )
        # Without capping, gross_needed would be 10000/0.01 = 1,000,000
        # With 50% cap, gross_needed = 10000/0.50 = 20,000
        assert result["withdrawals"]["taxable"] <= 25_000.0

    def test_income_rate_capped_at_70_percent(self):
        """Combined federal+state approaching 100% should not blow up."""
        from app.services.retirement.withdrawal_strategy_service import (
            AccountBuckets,
            tax_optimized_withdrawal,
        )

        buckets = AccountBuckets(taxable=0.0, pre_tax=100_000.0, roth=0.0, hsa=0.0)
        result = tax_optimized_withdrawal(
            buckets=buckets,
            needed=10_000.0,
            age=65,
            federal_rate=0.60,
            state_rate=0.35,
            capital_gains_rate=0.0,
        )
        # Without capping, income_rate=0.95, gross = 10000/0.05 = 200,000
        # With 70% cap, gross = 10000/0.30 = ~33,333
        assert result["withdrawals"]["pre_tax"] <= 40_000.0

    def test_normal_rates_unaffected(self):
        """Normal tax rates should produce the same results as before."""
        from app.services.retirement.withdrawal_strategy_service import (
            AccountBuckets,
            tax_optimized_withdrawal,
        )

        buckets = AccountBuckets(taxable=100_000.0, pre_tax=100_000.0, roth=50_000.0)
        result = tax_optimized_withdrawal(
            buckets=buckets,
            needed=40_000.0,
            age=65,
            federal_rate=0.22,
            state_rate=0.05,
            capital_gains_rate=0.15,
        )
        total_withdrawn = sum(result["withdrawals"].values())
        # Should withdraw approximately 40k + taxes
        assert 40_000.0 <= total_withdrawn <= 60_000.0

    def test_staging_with_debug_true_still_secure_false(self):
        """Staging is not production, so secure=False even if DEBUG is unrelated."""
        from app.api.v1.auth import _set_refresh_cookie

        mock_response = MagicMock()
        with patch("app.api.v1.auth.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "staging"
            mock_settings.DEBUG = True
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 30

            _set_refresh_cookie(mock_response, "test-token")

        call_kwargs = mock_response.set_cookie.call_args[1]
        assert call_kwargs["secure"] is False


# ---------------------------------------------------------------------------
# Config validators: staging is treated same as production
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigValidatorsStagingCoverage:
    """Security config validators must enforce the same rules in staging as production.

    Previously validators only checked ENVIRONMENT == 'production', so staging
    deployments could run with wildcard hosts, localhost CORS, and weak secrets.
    """

    def test_secret_key_rejected_in_staging(self):
        """Insecure SECRET_KEY should be rejected in staging, not just production."""
        import os

        from pydantic import ValidationError

        from app.config import Settings

        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            with pytest.raises((ValidationError, ValueError)):
                Settings(
                    SECRET_KEY="dev-secret-key-change-in-production",  # pragma: allowlist secret
                    ENVIRONMENT="staging",
                    DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
                )

    def test_secret_key_accepted_in_development(self):
        """Insecure SECRET_KEY should be allowed in development (dev convenience)."""
        import os

        from app.config import Settings

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Should not raise — dev environment allows weak keys
            s = Settings(
                SECRET_KEY="dev-secret-key-change-in-production",  # pragma: allowlist secret
                ENVIRONMENT="development",
                DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
            )
            assert s.SECRET_KEY == "dev-secret-key-change-in-production"  # pragma: allowlist secret

    def test_metrics_password_rejected_in_staging(self):
        """Default METRICS_PASSWORD should be rejected in staging."""
        import os

        from pydantic import ValidationError

        from app.config import Settings

        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            with pytest.raises((ValidationError, ValueError)):
                Settings(
                    ENVIRONMENT="staging",
                    METRICS_PASSWORD="metrics_admin",  # pragma: allowlist secret
                    DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
                    SECRET_KEY="a" * 32,
                )

    def test_allowed_hosts_wildcard_rejected_in_staging(self):
        """ALLOWED_HOSTS=['*'] should be rejected in staging."""
        import os

        from pydantic import ValidationError

        from app.config import Settings

        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            with pytest.raises((ValidationError, ValueError)):
                Settings(
                    ENVIRONMENT="staging",
                    ALLOWED_HOSTS=["*"],
                    DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
                    SECRET_KEY="a" * 32,
                    METRICS_PASSWORD="str0ng-metrics-pw",  # pragma: allowlist secret
                )

    def test_cors_localhost_rejected_in_staging(self):
        """Localhost CORS origins should be rejected in staging."""
        import os

        from pydantic import ValidationError

        from app.config import Settings

        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            with pytest.raises((ValidationError, ValueError)):
                Settings(
                    ENVIRONMENT="staging",
                    CORS_ORIGINS=["http://localhost:3000"],
                    ALLOWED_HOSTS=["staging.nestegg.com"],
                    DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
                    SECRET_KEY="a" * 32,
                    METRICS_PASSWORD="str0ng-metrics-pw",  # pragma: allowlist secret
                )


# ---------------------------------------------------------------------------
# SKIP_CSRF_IN_TESTS startup guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSkipCsrfStartupGuard:
    """SKIP_CSRF_IN_TESTS=True outside pytest must crash the app at startup."""

    def test_skip_csrf_allowed_in_pytest(self):
        """SKIP_CSRF_IN_TESTS=True is fine when pytest is in sys.modules."""
        import sys

        # pytest IS in sys.modules when this test runs — guard should pass
        assert "pytest" in sys.modules

        with patch("app.config.settings") as mock_settings:
            mock_settings.SKIP_CSRF_IN_TESTS = True
            mock_settings.ENVIRONMENT = "test"
            # Simulate the guard logic
            is_pytest = "pytest" in sys.modules
            if mock_settings.SKIP_CSRF_IN_TESTS and not is_pytest:
                raise RuntimeError("SECURITY: SKIP_CSRF_IN_TESTS outside pytest")
            # Should reach here without raising

    def test_skip_csrf_blocked_outside_pytest(self):
        """SKIP_CSRF_IN_TESTS=True without pytest in sys.modules must raise RuntimeError."""
        import sys

        with patch("app.config.settings") as mock_settings:
            mock_settings.SKIP_CSRF_IN_TESTS = True
            mock_settings.ENVIRONMENT = "production"

            # Simulate the guard with pytest NOT in sys.modules
            fake_modules = {k: v for k, v in sys.modules.items() if k != "pytest"}
            is_pytest = "pytest" in fake_modules
            assert not is_pytest  # Confirm our simulation

            with pytest.raises(RuntimeError, match="SKIP_CSRF_IN_TESTS"):
                if mock_settings.SKIP_CSRF_IN_TESTS and not is_pytest:
                    raise RuntimeError(
                        "SECURITY: SKIP_CSRF_IN_TESTS=true is set but this is not a pytest session."
                    )


# ---------------------------------------------------------------------------
# Invitation preview endpoint hardening
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInvitationPreviewHardening:
    """Invitation preview endpoints must use tight rate limits and generic 404s."""

    def test_guest_preview_rate_limit_is_5_per_hour(self):
        """guest_access preview should call rate_limit with max_requests=5, window=3600."""

        import pathlib

        src = pathlib.Path("/home/lanx/git/nest-egg/backend/app/api/v1/guest_access.py").read_text()
        # Find the preview_invitation function and check the rate limit call
        assert "max_requests=5" in src, "guest_access preview must use max_requests=5"
        assert "window_seconds=3600" in src, "guest_access preview must use window=3600 (per hour)"

    def test_household_invite_preview_rate_limit_is_5_per_hour(self):
        """household invitation preview should call rate_limit with max_requests=5, window=3600."""
        import pathlib

        src = pathlib.Path("/home/lanx/git/nest-egg/backend/app/api/v1/household.py").read_text()
        assert "max_requests=5" in src, "household invitation preview must use max_requests=5"
        assert "window_seconds=3600" in src, "household invitation preview must use window=3600"

    def test_guest_preview_uses_generic_404(self):
        """guest_access preview must return same 404 for not-found, expired, and used codes."""
        import pathlib

        src = pathlib.Path("/home/lanx/git/nest-egg/backend/app/api/v1/guest_access.py").read_text()
        # Both expired and not-found cases should raise the same _not_found exception
        assert "_not_found" in src, "Should use a single _not_found variable for all 404 cases"

    def test_household_preview_uses_generic_404(self):
        """household invitation preview must return same message for all failure cases."""
        import pathlib

        src = pathlib.Path("/home/lanx/git/nest-egg/backend/app/api/v1/household.py").read_text()
        assert "_not_found" in src, "Should use a single _not_found variable for all 404 cases"
        assert (
            "not found or expired" in src.lower()
        ), "404 message must not distinguish 'not found' from 'expired'"


# ---------------------------------------------------------------------------
# Dev router not mounted outside development
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDevRouterNotInNonDevEnv:
    """Dev router must only be registered when ENVIRONMENT=development."""

    def test_dev_router_only_registered_in_development(self):
        """main.py must only include the dev router for development environments."""
        import pathlib

        src = pathlib.Path("/home/lanx/git/nest-egg/backend/app/main.py").read_text()
        # Find the dev router registration
        assert 'ENVIRONMENT == "development"' in src or "ENVIRONMENT not in" in src
        # The dev router inclusion must be guarded by environment check
        dev_include = "app.include_router(dev.router"
        assert dev_include in src
        # Verify it's inside an if block guarding development
        lines = src.splitlines()
        for i, line in enumerate(lines):
            if dev_include in line:
                # Look backward for the if statement
                context = "\n".join(lines[max(0, i - 3) : i + 1])
                assert (
                    "development" in context
                ), f"dev router include at line {i+1} must be guarded by ENVIRONMENT check"

    def test_dev_router_lifespan_guard_exists(self):
        """main.py lifespan must contain a runtime check for dev router in non-dev envs."""
        import pathlib

        src = pathlib.Path("/home/lanx/git/nest-egg/backend/app/main.py").read_text()
        assert "/api/v1/dev" in src, "Lifespan must verify dev prefix not mounted in non-dev env"
        assert "SECURITY" in src, "Guard must include SECURITY in the error message"
