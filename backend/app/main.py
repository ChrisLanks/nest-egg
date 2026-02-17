"""FastAPI main application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.config import settings
from app.core.database import close_db, init_db
from app.services.snapshot_scheduler import snapshot_scheduler
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_size_limit import RequestSizeLimitMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
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
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("🚀 Starting Nest Egg API...")

    # Validate secrets and configuration (production only)
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
    await snapshot_scheduler.start()
    print("✅ Nest Egg API started successfully")

    yield

    # Shutdown
    print("🛑 Shutting down Nest Egg API...")
    await snapshot_scheduler.stop()
    await close_db()
    print("✅ Nest Egg API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler - Catch uncaught exceptions with PII redaction
app.add_middleware(ErrorHandlerMiddleware)

# Security middleware (production only)
if not settings.DEBUG:
    # HTTPS redirect - Force all requests to use HTTPS
    app.add_middleware(HTTPSRedirectMiddleware)

    # Trusted host - Prevent host header attacks
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Security headers - Always apply (dev and production)
app.add_middleware(SecurityHeadersMiddleware)

# Request size limit - Prevent DoS from large payloads (10MB limit)
app.add_middleware(RequestSizeLimitMiddleware, max_request_size=10 * 1024 * 1024)

# GZip compression for API responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add exception handler for validation errors
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"❌ Validation error: {exc}")
    print(f"❌ Error details: {exc.errors()}")
    print(f"❌ Request URL: {request.url}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
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
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/security-status")
async def security_status():
    """
    Security configuration status endpoint.

    Returns checklist of security configurations.
    Only shows status, never exposes actual secrets.
    """
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
            "Production ready" if security_score >= 90 else
            "Review failed checks before deploying to production"
        )
    }


# Import and include routers
from app.api.v1 import (
    auth, accounts, contributions, transactions, labels, rules, categories, dev, dashboard,
    income_expenses, plaid, holdings, enrichment, notifications, budgets, savings_goals,
    recurring_transactions, transaction_splits, transaction_merges, csv_import, household,
    subscriptions, reports, debt_payoff
)
from app.api.v1 import settings as settings_router

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(household.router, prefix="/api/v1", tags=["Household"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["Accounts"])
app.include_router(contributions.router, prefix="/api/v1", tags=["Contributions"])
app.include_router(holdings.router, prefix="/api/v1/holdings", tags=["Holdings"])
app.include_router(enrichment.router, prefix="/api/v1/enrichment", tags=["Enrichment"])
app.include_router(plaid.router, prefix="/api/v1/plaid", tags=["Plaid"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(labels.router, prefix="/api/v1/labels", tags=["Labels"])
app.include_router(rules.router, prefix="/api/v1/rules", tags=["Rules"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(income_expenses.router, prefix="/api/v1/income-expenses", tags=["Income vs Expenses"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(dev.router, prefix="/api/v1/dev", tags=["Development"])

# New feature routers
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(budgets.router, prefix="/api/v1/budgets", tags=["Budgets"])
app.include_router(savings_goals.router, prefix="/api/v1/savings-goals", tags=["Savings Goals"])
app.include_router(recurring_transactions.router, prefix="/api/v1/recurring-transactions", tags=["Recurring Transactions"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
app.include_router(transaction_splits.router, prefix="/api/v1/transaction-splits", tags=["Transaction Splits"])
app.include_router(transaction_merges.router, prefix="/api/v1/transaction-merges", tags=["Transaction Merges"])
app.include_router(csv_import.router, prefix="/api/v1/csv-import", tags=["CSV Import"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(debt_payoff.router, prefix="/api/v1/debt-payoff", tags=["Debt Payoff"])
