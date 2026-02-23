"""
Monitoring and observability API endpoints.

Provides endpoints for health checks, metrics, and rate limiting status.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.database import get_db
from app.dependencies import get_current_admin_user
from app.models.user import User
from app.services.rate_limit_service import get_rate_limit_service
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
    from app.config import settings

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
        timestamp=datetime.utcnow().isoformat(),
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
    rate_limit_keys = await redis.keys("rate_limit:*")

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

        reset_time = datetime.utcnow() + timedelta(seconds=ttl)

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
    from app.models.account import Account
    from app.models.transaction import Transaction
    from app.models.user import User

    # Get counts
    users_result = await db.execute(select(func.count(User.id)))
    users_count = users_result.scalar()

    accounts_result = await db.execute(select(func.count(Account.id)))
    accounts_count = accounts_result.scalar()

    transactions_result = await db.execute(select(func.count(Transaction.id)))
    transactions_count = transactions_result.scalar()

    # Get recent activity (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)

    new_users_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= yesterday)
    )
    new_users_24h = new_users_result.scalar()

    new_transactions_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.created_at >= yesterday)
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
        "timestamp": datetime.utcnow().isoformat(),
    }
