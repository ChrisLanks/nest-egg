"""
Monitoring and observability API endpoints.

Provides endpoints for health checks, metrics, and rate limiting status.
"""

from datetime import timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.core.database import get_db
from app.dependencies import get_current_admin_user
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.services.rate_limit_service import get_rate_limit_service
from app.utils.datetime_utils import utc_now
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
rate_limit_service = get_rate_limit_service()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: str
    database: str
    redis: str


class RateLimitStatus(BaseModel):
    """Rate limit status for an endpoint."""

    endpoint: str
    client_id: str
    requests: int
    limit: int
    window_seconds: int
    resets_at: str
    blocked: bool


class RateLimitDashboard(BaseModel):
    """Rate limiting dashboard data."""

    current_active_limits: List[RateLimitStatus]
    total_requests_last_hour: int
    blocked_requests_last_hour: int
    top_clients: List[Dict[str, Any]]
    top_endpoints: List[Dict[str, Any]]


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint for monitoring.

    Returns status of application and dependencies.
    """
    # Check database
    db_status = "ok"
    try:
        await db.execute(select(1))
    except Exception:
        db_status = "error"

    # Check Redis
    redis_status = "ok"
    try:
        redis = await rate_limit_service.get_redis()
        await redis.ping()
    except Exception:
        redis_status = "error"

    return HealthResponse(
        status="healthy" if db_status == "ok" and redis_status == "ok" else "degraded",
        version=settings.APP_VERSION,
        timestamp=utc_now().isoformat(),
        database=db_status,
        redis=redis_status,
    )


@router.get("/rate-limits", response_model=RateLimitDashboard)
async def get_rate_limit_dashboard(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Rate limiting dashboard showing current status and statistics.

    Only accessible by admin users.
    """
    redis = await rate_limit_service.get_redis()

    # Get all rate limit keys
    # Use SCAN instead of KEYS to avoid blocking Redis
    rate_limit_keys = []
    async for key in redis.scan_iter(match="rate_limit:*", count=100):
        rate_limit_keys.append(key)
        if len(rate_limit_keys) >= 500:  # Safety cap for admin dashboard
            break

    # Parse current active limits
    active_limits = []
    total_requests = 0
    blocked_count = 0
    client_request_counts = {}
    endpoint_request_counts = {}

    for key in rate_limit_keys:
        # Key format: rate_limit:endpoint:client_id
        parts = key.decode().split(":")
        if len(parts) < 3:
            continue

        endpoint = parts[1]
        client_id = parts[2]

        # Get request count
        count = await redis.get(key)
        if not count:
            continue

        count = int(count)
        total_requests += count

        # Get TTL
        ttl = await redis.ttl(key)

        # Track by client
        if client_id not in client_request_counts:
            client_request_counts[client_id] = 0
        client_request_counts[client_id] += count

        # Track by endpoint
        if endpoint not in endpoint_request_counts:
            endpoint_request_counts[endpoint] = 0
        endpoint_request_counts[endpoint] += count

        # Determine if blocked (simplified - would need to check actual limits)
        # For now, assume limit is stored separately or use a default
        limit = 100  # Would get from actual rate limit config
        is_blocked = count >= limit

        if is_blocked:
            blocked_count += 1

        reset_time = utc_now() + timedelta(seconds=ttl)

        active_limits.append(
            RateLimitStatus(
                endpoint=endpoint,
                client_id=client_id,
                requests=count,
                limit=limit,
                window_seconds=60,  # Would get from actual config
                resets_at=reset_time.isoformat(),
                blocked=is_blocked,
            )
        )

    # Sort and get top clients
    top_clients = sorted(
        [{"client_id": k, "requests": v} for k, v in client_request_counts.items()],
        key=lambda x: x["requests"],
        reverse=True,
    )[:10]

    # Sort and get top endpoints
    top_endpoints = sorted(
        [{"endpoint": k, "requests": v} for k, v in endpoint_request_counts.items()],
        key=lambda x: x["requests"],
        reverse=True,
    )[:10]

    return RateLimitDashboard(
        current_active_limits=active_limits[:50],  # Limit to 50 most recent
        total_requests_last_hour=total_requests,
        blocked_requests_last_hour=blocked_count,
        top_clients=top_clients,
        top_endpoints=top_endpoints,
    )


@router.get("/system-stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    System statistics for monitoring dashboard.

    Returns counts of key entities and recent activity.
    Only accessible by admin users.
    """
    org_id = current_user.organization_id

    # Scope all counts to the admin's organization to prevent cross-tenant data leak
    users_result = await db.execute(
        select(func.count(User.id)).where(User.organization_id == org_id)
    )
    users_count = users_result.scalar()

    accounts_result = await db.execute(
        select(func.count(Account.id)).where(Account.organization_id == org_id)
    )
    accounts_count = accounts_result.scalar()

    transactions_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.organization_id == org_id)
    )
    transactions_count = transactions_result.scalar()

    # Get recent activity (last 24 hours) within the organization
    yesterday = utc_now() - timedelta(days=1)

    new_users_result = await db.execute(
        select(func.count(User.id)).where(
            User.organization_id == org_id,
            User.created_at >= yesterday,
        )
    )
    new_users_24h = new_users_result.scalar()

    new_transactions_result = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.organization_id == org_id,
            Transaction.created_at >= yesterday,
        )
    )
    new_transactions_24h = new_transactions_result.scalar()

    return {
        "totals": {
            "users": users_count,
            "accounts": accounts_count,
            "transactions": transactions_count,
        },
        "last_24_hours": {
            "new_users": new_users_24h,
            "new_transactions": new_transactions_24h,
        },
        "timestamp": utc_now().isoformat(),
    }


# ---------------------------------------------------------------------------
# GDPR Article 30 — Records of Processing Activities (RoPA)
# ---------------------------------------------------------------------------

_ROPA = [
    {
        "activity": "User authentication",
        "purpose": "Verify user identity and issue access tokens",
        "data_categories": ["email", "password_hash", "failed_login_attempts", "locked_until"],
        "legal_basis": "Contractual necessity (Art. 6(1)(b))",
        "retention": "Until account deletion",
        "recipients": ["Internal system only"],
    },
    {
        "activity": "Session management",
        "purpose": "Maintain authenticated sessions via refresh tokens",
        "data_categories": ["refresh_token_jti", "ip_address", "user_agent"],
        "legal_basis": "Contractual necessity (Art. 6(1)(b))",
        "retention": "30 days (tokens expire and are purged)",
        "recipients": ["Internal system only"],
    },
    {
        "activity": "Personal finance tracking",
        "purpose": "Store and display user accounts, transactions, holdings, and budgets",
        "data_categories": [
            "account_names", "account_balances", "transaction_amounts",
            "transaction_dates", "merchant_names", "categories",
            "investment_holdings", "budget_limits",
        ],
        "legal_basis": "Contractual necessity (Art. 6(1)(b))",
        "retention": "Until account deletion",
        "recipients": ["Internal system only"],
    },
    {
        "activity": "Household data sharing",
        "purpose": "Allow household members to view/edit each other's financial data with explicit permission",
        "data_categories": ["permission_grants", "resource_types", "grantee_user_ids"],
        "legal_basis": "Explicit consent (Art. 6(1)(a)) — user initiates each grant",
        "retention": "Until grant is revoked or account is deleted",
        "recipients": ["Other household members (grantees) — limited to granted resource types"],
    },
    {
        "activity": "External bank data import (Plaid)",
        "purpose": "Fetch account balances and transactions from linked bank accounts",
        "data_categories": [
            "plaid_access_token (encrypted)", "account_ids", "transaction_data",
        ],
        "legal_basis": "Explicit consent (Art. 6(1)(a)) — user links each institution",
        "retention": "Access token until user unlinks; transaction data until account deletion",
        "recipients": ["Plaid Inc. (data processor) — subject to Plaid Privacy Policy"],
    },
    {
        "activity": "External bank data import (Teller)",
        "purpose": "Fetch account balances and transactions from linked bank accounts",
        "data_categories": [
            "teller_access_token (encrypted)", "account_ids", "transaction_data",
        ],
        "legal_basis": "Explicit consent (Art. 6(1)(a)) — user links each institution",
        "retention": "Access token until user unlinks; transaction data until account deletion",
        "recipients": ["Teller Inc. (data processor) — subject to Teller Privacy Policy"],
    },
    {
        "activity": "Retirement planning calculations",
        "purpose": "Calculate required minimum distributions (RMDs) and retirement projections",
        "data_categories": ["birthdate (encrypted at rest)", "target_retirement_date"],
        "legal_basis": "Explicit consent (Art. 6(1)(a)) — user optionally provides birthdate",
        "retention": "Until removed by user or account deletion",
        "recipients": ["Internal system only"],
    },
    {
        "activity": "Multi-factor authentication",
        "purpose": "Provide optional TOTP-based second factor for account security",
        "data_categories": ["totp_secret (encrypted)", "backup_codes (encrypted)"],
        "legal_basis": "Legitimate interest (Art. 6(1)(f)) — security of user data",
        "retention": "Until MFA is disabled or account is deleted",
        "recipients": ["Internal system only"],
    },
    {
        "activity": "Consent records",
        "purpose": "Record user consent to Terms of Service and Privacy Policy (GDPR Art. 7)",
        "data_categories": ["consent_type", "version", "consented_at", "ip_address"],
        "legal_basis": "Legal obligation (Art. 6(1)(c)) — GDPR Art. 7 record-keeping",
        "retention": "3 years after account deletion (legal obligation)",
        "recipients": ["Internal system only"],
    },
    {
        "activity": "Permission grant audit log",
        "purpose": "Immutable record of all permission grant changes (GDPR Art. 30)",
        "data_categories": [
            "grantor_id", "grantee_id", "resource_type", "actions_before",
            "actions_after", "actor_id", "ip_address", "occurred_at",
        ],
        "legal_basis": "Legal obligation (Art. 6(1)(c)) — audit trail",
        "retention": "Until grantor's account is deleted",
        "recipients": ["Internal system only"],
    },
    {
        "activity": "Error monitoring (Sentry)",
        "purpose": "Track application errors for reliability and security incident detection",
        "data_categories": ["stack_traces", "request_paths", "anonymised_user_ids"],
        "legal_basis": "Legitimate interest (Art. 6(1)(f)) — application security and stability",
        "retention": "90 days (Sentry default retention)",
        "recipients": [
            "Sentry Inc. (data processor) — PII scrubbed before transmission "
            "(no email, no token, no financial data)"
        ],
    },
    {
        "activity": "Request logging",
        "purpose": "Structured access logs for security monitoring and debugging",
        "data_categories": [
            "request_id", "http_method", "path", "status_code",
            "duration_ms", "user_id (anonymised)", "ip_address",
        ],
        "legal_basis": "Legitimate interest (Art. 6(1)(f)) — security monitoring",
        "retention": "30 days (log rotation)",
        "recipients": ["Internal system only"],
    },
    {
        "activity": "Data export (GDPR Art. 20)",
        "purpose": "Provide users a machine-readable copy of all their data",
        "data_categories": ["All data categories listed above"],
        "legal_basis": "Legal obligation (Art. 6(1)(c)) — GDPR Art. 20 data portability",
        "retention": "Export files are generated on demand and not stored server-side",
        "recipients": ["User themselves only"],
    },
]


@router.get("/data-processing-activities")
async def list_data_processing_activities(
    _admin: User = Depends(get_current_admin_user),
):
    """
    GDPR Article 30 — Records of Processing Activities (RoPA).

    Returns a machine-readable list of all data processing activities,
    including legal basis, data categories, and recipient categories.

    Restricted to org admins.
    """
    return {
        "version": "2026-02",
        "last_updated": "2026-02-23",
        "controller": "Nest Egg",
        "activities": _ROPA,
    }
