"""
Prometheus metrics instrumentation for monitoring application performance.

This module provides Prometheus metrics for:
- HTTP requests (latency, status codes, throughput)
- Database query performance
- Celery task execution
- Rate limiting hits
- Business metrics (users, transactions, accounts)

Metrics are exposed on a SEPARATE admin port (default 9090) protected by HTTP Basic Auth.
They are NOT exposed on the main API port (8000).

Dev access: curl -u admin:metrics_admin http://localhost:9090/metrics
Prod: override METRICS_USERNAME and METRICS_PASSWORD in environment.
"""

import base64
import hmac

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import ASGIApp

from app.config import settings


# Custom Prometheus metrics

# HTTP metrics
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size",
)

db_connection_pool_available = Gauge(
    "db_connection_pool_available",
    "Available connections in database pool",
)

# Celery metrics
celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name", "status"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks executed",
    ["task_name", "status"],
)

# Rate limiting metrics
rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits (requests blocked)",
    ["endpoint"],
)

rate_limit_requests_total = Counter(
    "rate_limit_requests_total",
    "Total requests subject to rate limiting",
    ["endpoint"],
)

# Business metrics
users_total = Gauge(
    "users_total",
    "Total number of registered users",
)

transactions_total = Gauge(
    "transactions_total",
    "Total number of transactions",
)

accounts_total = Gauge(
    "accounts_total",
    "Total number of linked accounts",
)

plaid_syncs_total = Counter(
    "plaid_syncs_total",
    "Total Plaid sync operations",
    ["status"],  # success, failure
)

budget_alerts_total = Counter(
    "budget_alerts_total",
    "Total budget alerts triggered",
    ["priority"],  # low, medium, high
)


def setup_metrics(app: FastAPI) -> None:
    """
    Instrument the FastAPI app with Prometheus metrics collectors.

    Does NOT expose a /metrics route on the main API port.
    Metrics are served on a separate admin port via create_metrics_app().

    Args:
        app: FastAPI application instance
    """
    # Use prometheus-fastapi-instrumentator for automatic HTTP metrics
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/docs", "/openapi.json"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics
    instrumentator.add(
        metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    instrumentator.add(
        metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    instrumentator.add(
        metrics.latency(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
        )
    )

    instrumentator.add(
        metrics.requests(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    # Instrument only — do NOT expose /metrics on the main port
    instrumentator.instrument(app)


def create_metrics_app() -> ASGIApp:
    """
    Create a minimal ASGI app that serves /metrics behind HTTP Basic Auth.

    This app runs on a separate admin port (METRICS_ADMIN_PORT, default 9090)
    so Prometheus metrics are never exposed on the public API port.

    Dev access:
        curl -u admin:metrics_admin http://localhost:9090/metrics

    Prod: override METRICS_USERNAME / METRICS_PASSWORD in environment.
    """
    async def metrics_endpoint(request: Request) -> Response:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return Response(
                content="Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="metrics"'},
            )

        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8", errors="replace")
            username, password = decoded.split(":", 1)
        except Exception:
            return Response(
                content="Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="metrics"'},
            )

        if not (hmac.compare_digest(username, settings.METRICS_USERNAME) and hmac.compare_digest(password, settings.METRICS_PASSWORD)):
            return Response(
                content="Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="metrics"'},
            )

        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return Starlette(routes=[Route("/metrics", metrics_endpoint)])


# Middleware to track custom metrics
class MetricsMiddleware:
    """Middleware to collect custom metrics for each request."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)


def track_rate_limit_hit(endpoint: str, ip: str = "") -> None:
    """Track when a rate limit is hit."""
    rate_limit_hits_total.labels(endpoint=endpoint).inc()


def track_rate_limit_request(endpoint: str) -> None:
    """Track a request subject to rate limiting."""
    rate_limit_requests_total.labels(endpoint=endpoint).inc()


def track_celery_task(task_name: str, status: str, duration_seconds: float) -> None:
    """Track Celery task execution."""
    celery_task_duration_seconds.labels(task_name=task_name, status=status).observe(
        duration_seconds
    )
    celery_tasks_total.labels(task_name=task_name, status=status).inc()


def track_plaid_sync(status: str) -> None:
    """Track Plaid sync operation."""
    plaid_syncs_total.labels(status=status).inc()


def track_budget_alert(priority: str) -> None:
    """Track budget alert triggered."""
    budget_alerts_total.labels(priority=priority).inc()


def update_business_metrics(
    users: int = None,
    transactions: int = None,
    accounts: int = None,
) -> None:
    """Update business metrics gauges."""
    if users is not None:
        users_total.set(users)
    if transactions is not None:
        transactions_total.set(transactions)
    if accounts is not None:
        accounts_total.set(accounts)
