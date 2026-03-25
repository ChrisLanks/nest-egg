"""FastAPI main application."""

import logging
from contextlib import asynccontextmanager
from decimal import Decimal

_logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    accounts,
    attachments,
    auth,
    bank_linking,
    budgets,
    bulk_operations,
    categories,
    contributions,
    csv_import,
    dashboard,
    debt_payoff,
    dev,
    dividend_income,
    education,
    enhanced_trends,
    enrichment,
    financial_planning,
    financial_templates,
    fire,
    guest_access,
    holdings,
    household,
    income_expenses,
    labels,
    market_data,
    monitoring,
    notifications,
    onboarding,
    permissions,
    plaid,
    rebalancing,
    recurring_transactions,
    rental_properties,
    reports,
    retirement,
    rules,
    savings_goals,
    smart_insights,
    subscriptions,
    capital_gains_harvesting,
    charitable_giving,
    estate,
    hsa,
    loan_modeling,
    net_worth_attribution,
    stress_test,
    tax_advisor,
    tax_buckets,
    tax_lots,
    teller,
    transaction_merges,
    transaction_splits,
    transactions,
)
from app.api.v1 import settings as settings_router
from app.config import settings
from app.core.database import close_db, init_db
from app.core.logging_config import setup_logging
from app.core.metrics import create_metrics_app, setup_metrics
from app.dependencies import get_current_user, get_organization_scoped_user
from app.middleware.anomaly_detection import AnomalyDetectionMiddleware
from app.middleware.csrf_protection import CSRFProtectionMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import (
    AuditLogMiddleware,
    RequestLoggingMiddleware,
    UserContextMiddleware,
)
from app.middleware.request_size_limit import RequestSizeLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models.user import User as UserModel
from app.services.secrets_validation_service import secrets_validation_service

# Initialize Sentry for error tracking and monitoring (optional)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    print("⚠️  Sentry SDK not installed - error tracking disabled")
    print("   Install with: pip install sentry-sdk[fastapi]")

if SENTRY_AVAILABLE and settings.SENTRY_DSN:

    def _filter_sensitive_data(event):
        """Filter sensitive data from Sentry events before sending."""
        # Remove sensitive headers
        if "request" in event and "headers" in event["request"]:
            headers = event["request"]["headers"]
            sensitive_headers = ["authorization", "cookie", "x-api-key", "x-auth-token"]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[Filtered]"

        # Remove sensitive query parameters
        if "request" in event and "query_string" in event["request"]:
            sensitive_params = ["token", "password", "api_key", "secret"]
            query = event["request"].get("query_string", "")
            for param in sensitive_params:
                if param in query.lower():
                    event["request"]["query_string"] = "[Filtered]"
                    break

        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring
        # In production, you may want to reduce this to save quota (e.g., 0.1 for 10%)
        traces_sample_rate=0.1 if not settings.DEBUG else 1.0,
        # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions
        # Helps identify performance bottlenecks
        profiles_sample_rate=0.1 if not settings.DEBUG else 1.0,
        # Send PII (personally identifiable information) - set to False in production
        send_default_pii=False,
        # Environment tracking
        environment="development" if settings.DEBUG else "production",
        # Release tracking for better error grouping
        release=f"{settings.APP_NAME}@{settings.APP_VERSION}",
        # Attach stacktrace to all messages
        attach_stacktrace=True,
        # Filter out sensitive data from breadcrumbs
        before_send=_filter_sensitive_data,
    )
    print(f"✅ Sentry initialized for {'development' if settings.DEBUG else 'production'}")
elif SENTRY_AVAILABLE and not settings.SENTRY_DSN:
    print("⚠️  Sentry DSN not configured - error tracking disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: F811 — shadows module-level `app` intentionally
    """Application lifespan manager."""
    import asyncio

    # Startup
    print("🚀 Starting Nest Egg API...")

    # Initialize structured logging
    setup_logging()
    print("✅ Logging configured")

    # ── Security startup assertions ────────────────────────────────────────
    # These run unconditionally on every startup so misconfigurations are
    # caught immediately — not discovered during an incident.

    # Guard 1: SKIP_CSRF_IN_TESTS must never be set outside a pytest session.
    # Setting this in .env or via an env var in any deployed environment
    # silently disables all CSRF protection for every user.
    if settings.SKIP_CSRF_IN_TESTS:
        import sys

        _is_pytest = "pytest" in sys.modules
        if not _is_pytest:
            raise RuntimeError(
                "SECURITY: SKIP_CSRF_IN_TESTS=true is set but this is not a pytest session. "
                "This flag disables CSRF protection for all users. "
                "Remove it from your .env / environment variables immediately."
            )

    # Guard 2: dev router must never be reachable outside development.
    # The dev router contains endpoints that dump data, seed fake accounts,
    # and create backdoor users with a known password ('test1234').
    # FastAPI passes the app instance as the `app` parameter to lifespan,
    # so we can inspect its routes directly here.
    if settings.ENVIRONMENT not in ("development", "test"):
        _dev_prefix = "/api/v1/dev"
        _dev_routes = [
            r for r in app.routes if hasattr(r, "path") and r.path.startswith(_dev_prefix)
        ]
        if _dev_routes:
            raise RuntimeError(
                f"SECURITY: Dev router is mounted at {_dev_prefix} in "
                f"ENVIRONMENT={settings.ENVIRONMENT!r}. "
                "This exposes data-dump, seed, and backdoor-account endpoints. "
                "Check main.py router registration."
            )

    # Guard 3: warn when running multiple workers with in-memory rate limiting.
    # Each worker maintains independent counters, so effective rate limits are
    # multiplied by worker count — an attacker can distribute requests to evade.
    if settings.ENVIRONMENT not in ("development", "test"):
        import os

        workers = int(os.getenv("WEB_CONCURRENCY", os.getenv("UVICORN_WORKERS", "1")))
        redis_url = settings.REDIS_URL if hasattr(settings, "REDIS_URL") else None
        if workers > 1 and not redis_url:
            _logger.warning(
                "SECURITY WARNING: Running %d workers without Redis. "
                "Rate limiting and anomaly detection are per-process — "
                "effective limits are %dx the configured values. "
                "Set REDIS_URL to enable global rate limiting.",
                workers,
                workers,
            )

    # ── End security startup assertions ───────────────────────────────────

    # Validate secrets and configuration (non-dev environments)
    if not settings.DEBUG:
        print("🔒 Validating production secrets...")
        validation_result = secrets_validation_service.validate_production_secrets()

        if validation_result["errors"]:
            print("❌ CRITICAL: Production secrets validation failed:")
            for error in validation_result["errors"]:
                print(f"  - {error}")
            raise RuntimeError("Application cannot start with invalid production configuration")

        if validation_result["warnings"]:
            print("⚠️  Production configuration warnings:")
            for warning in validation_result["warnings"]:
                print(f"  - {warning}")

        print("✅ Production secrets validated successfully")
    else:
        print("⚠️  Running in DEBUG mode - secrets validation skipped")

    await init_db()

    # Launch Prometheus metrics on a separate admin port (protected by basic auth)
    if settings.METRICS_ENABLED:
        import uvicorn

        metrics_asgi = create_metrics_app()
        # Bind to 0.0.0.0 only when an allowlist is configured (so remote
        # Prometheus scrapers can reach it); otherwise bind to localhost.
        metrics_host = "0.0.0.0" if settings.METRICS_ALLOWED_HOSTS else "127.0.0.1"  # nosec B104
        metrics_config = uvicorn.Config(
            metrics_asgi,
            host=metrics_host,
            port=settings.METRICS_ADMIN_PORT,
            log_level="warning",
        )
        metrics_server = uvicorn.Server(metrics_config)
        asyncio.create_task(metrics_server.serve())
        print(f"✅ Metrics admin server started on port {settings.METRICS_ADMIN_PORT}")

    print("✅ Nest Egg API started successfully")

    yield

    # Shutdown
    print("🛑 Shutting down Nest Egg API...")
    await close_db()
    print("✅ Nest Egg API shutdown complete")


# Create FastAPI application
# OpenAPI schema is always available for self-documentation.
# Interactive docs (Swagger UI / ReDoc) are only enabled in development.
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Personal finance tracking API for households. "
        "Manages accounts, transactions, investments, budgets, savings goals, "
        "retirement planning, education planning, rental property P&L, "
        "financial health scoring, investment fee analysis, "
        "and bank integrations (Plaid, Teller, MX).\n\n"
        "**Authentication:** JWT access tokens via `Authorization: Bearer <token>` header. "
        "Refresh tokens are stored in httpOnly cookies.\n\n"
        "**Multi-tenancy:** All data is scoped to an organization (household). "
        "Users within an organization can share data via the permissions system.\n\n"
        "**OpenAPI schema:** Always available at `/openapi.json`."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Guest access: override get_current_user so all endpoints automatically
# resolve X-Household-Id header and scope data to the guest household.
app.dependency_overrides[get_current_user] = get_organization_scoped_user

# Instrument the app with Prometheus (metrics served on admin port, not here)
if settings.METRICS_ENABLED:
    setup_metrics(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Requested-With",
        "X-Household-Id",
    ],
)

# Error handler - Catch uncaught exceptions with PII redaction
app.add_middleware(ErrorHandlerMiddleware)

# Security middleware (production only)
if not settings.DEBUG:
    # HTTPS redirect - Force all requests to use HTTPS
    app.add_middleware(HTTPSRedirectMiddleware)

    # Trusted host - Prevent host header attacks
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Security headers - Always apply (dev and production)
app.add_middleware(SecurityHeadersMiddleware)

# CSRF protection - Protect against cross-site request forgery
app.add_middleware(CSRFProtectionMiddleware)

# Global rate limiting - Prevent DoS attacks (1000 req/min per user/IP)
app.add_middleware(RateLimitMiddleware)

# Request size limit - Prevent DoS from large payloads (10MB limit)
app.add_middleware(RequestSizeLimitMiddleware, max_request_size=10 * 1024 * 1024)

# GZip compression for API responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Middleware execution order (Starlette processes last-added first on request):
# Request → AnomalyDetection → UserContext → RequestLogging → AuditLog → route
# UserContext extracts user from JWT first, then RequestLogging and AuditLog can use it.

# Audit logging - Track sensitive operations (innermost — runs after all context is set)
app.add_middleware(AuditLogMiddleware)

# Request logging - Track all API requests, assign request_id (reads user_email from state)
app.add_middleware(RequestLoggingMiddleware)

# User context extraction - Extract user from JWT/cookie for logging (sets user_email/user_id)
app.add_middleware(UserContextMiddleware)

# Anomaly detection - Emit CRITICAL logs on breach signals (outermost — runs first)
app.add_middleware(AnomalyDetectionMiddleware)


def _make_json_serializable(obj):
    """Recursively convert non-JSON-serializable types to serializable ones."""
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_serializable(i) for i in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, type):
        return str(obj)
    if isinstance(obj, Exception):
        return str(obj)
    return obj


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    _logger.debug("Validation error on %s: %s", request.url, exc.errors())
    errors = _make_json_serializable(exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with real dependency checks.

    Returns 200 if the database is reachable, 503 otherwise.
    Unauthenticated so Docker HEALTHCHECK / load balancers can use it.
    """
    from sqlalchemy import text

    from app.core.database import AsyncSessionLocal

    checks = {}

    # Database connectivity
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unreachable"

    all_ok = all(v == "ok" for v in checks.values())

    if not all_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "checks": checks},
        )

    return {"status": "healthy", "checks": checks}


@app.get("/security-status")
async def security_status(current_user: UserModel = Depends(get_current_user)):
    """
    Security configuration status endpoint — requires org admin authentication.

    Returns checklist of security configurations.
    Only shows status, never exposes actual secrets.
    """
    # Block guests — even if they're admin in their home org, they shouldn't
    # see the security status of a household they're visiting.
    if getattr(current_user, "_is_guest", False):
        raise HTTPException(status_code=403, detail="Guests cannot view security status")
    if not current_user.is_org_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    checklist = secrets_validation_service.generate_security_checklist()

    # Calculate overall security score
    total_checks = len(checklist)
    passed_checks = sum(1 for passed in checklist.values() if passed)
    security_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    return {
        "security_score": round(security_score, 1),
        "checks_passed": passed_checks,
        "checks_total": total_checks,
        "checklist": checklist,
        "environment": "production" if not settings.DEBUG else "development",
        "recommendation": (
            "Production ready"
            if security_score >= 90
            else "Review failed checks before deploying to production"
        ),
    }


# ---------------------------------------------------------------------------
# Router registration
#
# Routers are split into two groups:
#
#   HOUSEHOLD-SCOPED (guest-eligible)
#     Use dependencies=[Depends(get_organization_scoped_user)] so that the
#     X-Household-Id header is honoured on every request.  When the header is
#     absent the dependency behaves identically to get_current_user.
#     Guests with the "viewer" role get read-only access (POST/PUT/PATCH/DELETE
#     are rejected at the dependency level).  Guests with the "advisor" role
#     get full read+write access to the host household.
#     Default access for authenticated members (no header) is read+write
#     limited to their own organisation.
#
#   MEMBER/ADMIN-ONLY (no guest access)
#     Use plain get_current_user (or get_current_admin_user inside the
#     endpoint).  Guests are never allowed here regardless of role.
# ---------------------------------------------------------------------------

_guest_dep = [Depends(get_organization_scoped_user)]

# ------ MEMBER/ADMIN-ONLY routers (no guest access) ------
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Monitoring"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(household.router, prefix="/api/v1", tags=["Household"])
app.include_router(bank_linking.router, prefix="/api/v1/bank-linking", tags=["Bank Linking"])
app.include_router(plaid.router, prefix="/api/v1/plaid", tags=["Plaid"])
app.include_router(teller.router, prefix="/api/v1/teller", tags=["Teller"])
app.include_router(market_data.router, prefix="/api/v1/market-data", tags=["Market Data"])
app.include_router(enrichment.router, prefix="/api/v1/enrichment", tags=["Enrichment"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(permissions.router, prefix="/api/v1/permissions", tags=["Permissions"])
app.include_router(csv_import.router, prefix="/api/v1/csv-import", tags=["CSV Import"])
app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding"])
app.include_router(guest_access.router, prefix="/api/v1/guest-access", tags=["Guest Access"])
if settings.ENVIRONMENT == "development":
    app.include_router(dev.router, prefix="/api/v1/dev", tags=["Development"])

# ------ HOUSEHOLD-SCOPED routers (guest-eligible) ------
app.include_router(
    accounts.router, prefix="/api/v1/accounts", tags=["Accounts"], dependencies=_guest_dep
)
app.include_router(
    contributions.router, prefix="/api/v1", tags=["Contributions"], dependencies=_guest_dep
)
app.include_router(
    holdings.router, prefix="/api/v1/holdings", tags=["Holdings"], dependencies=_guest_dep
)
app.include_router(
    transactions.router,
    prefix="/api/v1/transactions",
    tags=["Transactions"],
    dependencies=_guest_dep,
)
app.include_router(labels.router, prefix="/api/v1/labels", tags=["Labels"], dependencies=_guest_dep)
app.include_router(rules.router, prefix="/api/v1/rules", tags=["Rules"], dependencies=_guest_dep)
app.include_router(
    categories.router,
    prefix="/api/v1/categories",
    tags=["Categories"],
    dependencies=_guest_dep,
)
app.include_router(
    dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"], dependencies=_guest_dep
)
app.include_router(
    income_expenses.router,
    prefix="/api/v1/income-expenses",
    tags=["Income vs Expenses"],
    dependencies=_guest_dep,
)
app.include_router(
    notifications.router,
    prefix="/api/v1/notifications",
    tags=["Notifications"],
    dependencies=_guest_dep,
)
app.include_router(
    budgets.router, prefix="/api/v1/budgets", tags=["Budgets"], dependencies=_guest_dep
)
app.include_router(
    financial_templates.router,
    prefix="/api/v1/financial-templates",
    tags=["Financial Templates"],
    dependencies=_guest_dep,
)
app.include_router(
    savings_goals.router,
    prefix="/api/v1/savings-goals",
    tags=["Savings Goals"],
    dependencies=_guest_dep,
)
app.include_router(
    recurring_transactions.router,
    prefix="/api/v1/recurring-transactions",
    tags=["Recurring Transactions"],
    dependencies=_guest_dep,
)
app.include_router(
    subscriptions.router,
    prefix="/api/v1/subscriptions",
    tags=["Subscriptions"],
    dependencies=_guest_dep,
)
app.include_router(
    transaction_splits.router,
    prefix="/api/v1/transaction-splits",
    tags=["Transaction Splits"],
    dependencies=_guest_dep,
)
app.include_router(
    transaction_merges.router,
    prefix="/api/v1/transaction-merges",
    tags=["Transaction Merges"],
    dependencies=_guest_dep,
)
app.include_router(
    reports.router, prefix="/api/v1/reports", tags=["Reports"], dependencies=_guest_dep
)
app.include_router(
    debt_payoff.router,
    prefix="/api/v1/debt-payoff",
    tags=["Debt Payoff"],
    dependencies=_guest_dep,
)
app.include_router(
    rebalancing.router,
    prefix="/api/v1/rebalancing",
    tags=["Rebalancing"],
    dependencies=_guest_dep,
)
app.include_router(
    retirement.router,
    prefix="/api/v1/retirement",
    tags=["Retirement Planning"],
    dependencies=_guest_dep,
)
app.include_router(
    education.router,
    prefix="/api/v1/education",
    tags=["Education Planning"],
    dependencies=_guest_dep,
)
app.include_router(
    fire.router, prefix="/api/v1/fire", tags=["FIRE Metrics"], dependencies=_guest_dep
)
app.include_router(
    rental_properties.router,
    prefix="/api/v1/rental-properties",
    tags=["Rental Properties"],
    dependencies=_guest_dep,
)
app.include_router(tax_lots.router, prefix="/api/v1", tags=["Tax Lots"], dependencies=_guest_dep)
app.include_router(
    attachments.router, prefix="/api/v1", tags=["Attachments"], dependencies=_guest_dep
)
app.include_router(
    bulk_operations.router,
    prefix="/api/v1/bulk-operations",
    tags=["Bulk Operations"],
    dependencies=_guest_dep,
)
app.include_router(
    dividend_income.router,
    prefix="/api/v1/dividend-income",
    tags=["Dividend Income"],
    dependencies=_guest_dep,
)
app.include_router(
    tax_advisor.router,
    prefix="/api/v1/tax-advisor",
    tags=["Tax Advisor"],
    dependencies=_guest_dep,
)
app.include_router(
    tax_buckets.router,
    prefix="/api/v1",
    tags=["Tax Buckets"],
    dependencies=_guest_dep,
)
app.include_router(
    enhanced_trends.router,
    prefix="/api/v1/trends",
    tags=["Enhanced Trends"],
    dependencies=_guest_dep,
)
app.include_router(
    smart_insights.router,
    prefix="/api/v1/smart-insights",
    tags=["Smart Insights"],
    dependencies=_guest_dep,
)
app.include_router(
    financial_planning.router,
    prefix="/api/v1/financial-planning",
    tags=["Financial Planning"],
    dependencies=_guest_dep,
)
app.include_router(
    capital_gains_harvesting.router,
    prefix="/api/v1/capital-gains-harvesting",
    tags=["Capital Gains Harvesting"],
    dependencies=_guest_dep,
)
app.include_router(
    stress_test.router,
    prefix="/api/v1/stress-test",
    tags=["Portfolio Stress Testing"],
    dependencies=_guest_dep,
)
app.include_router(
    net_worth_attribution.router,
    prefix="/api/v1/net-worth-attribution",
    tags=["Net Worth Attribution"],
    dependencies=_guest_dep,
)
app.include_router(
    hsa.router,
    prefix="/api/v1/hsa",
    tags=["HSA Optimization"],
    dependencies=_guest_dep,
)
app.include_router(
    estate.router,
    prefix="/api/v1/estate",
    tags=["Estate Planning"],
    dependencies=_guest_dep,
)
app.include_router(
    loan_modeling.router,
    prefix="/api/v1/loan-modeling",
    tags=["Loan Modeling"],
    dependencies=_guest_dep,
)
app.include_router(
    charitable_giving.router,
    prefix="/api/v1/charitable-giving",
    tags=["Charitable Giving"],
    dependencies=_guest_dep,
)
