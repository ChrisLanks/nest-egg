"""FastAPI main application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import close_db, init_db
from app.services.snapshot_scheduler import snapshot_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    await snapshot_scheduler.start()
    yield
    # Shutdown
    await snapshot_scheduler.stop()
    await close_db()


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
