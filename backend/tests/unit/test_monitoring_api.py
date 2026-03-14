"""Unit tests for monitoring API endpoints — covers health check, rate-limits dashboard,
system-stats, circuit-breakers, data-processing-activities, jobs, and job status."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.monitoring import (
    _ROPA,
    HealthResponse,
    get_active_jobs,
    get_circuit_breaker_status,
    get_job_status,
    get_rate_limit_dashboard,
    get_system_stats,
    health_check,
    list_data_processing_activities,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin_user(org_id=None):
    user = MagicMock()
    user.id = uuid4()
    user.organization_id = org_id or uuid4()
    user.is_org_admin = True
    return user


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMonitoringHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_when_all_ok(self):
        """Should return healthy when DB and Redis are ok."""
        db = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(return_value=mock_redis)

            result = await health_check(db=db)

        assert isinstance(result, HealthResponse)
        assert result.status == "healthy"
        assert result.database == "ok"
        assert result.redis == "ok"

    @pytest.mark.asyncio
    async def test_degraded_when_db_fails(self):
        """Should return degraded when DB query fails."""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB down"))

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(return_value=mock_redis)

            result = await health_check(db=db)

        assert result.status == "degraded"
        assert result.database == "error"
        assert result.redis == "ok"

    @pytest.mark.asyncio
    async def test_degraded_when_redis_fails(self):
        """Should return degraded when Redis ping fails."""
        db = AsyncMock()

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(side_effect=Exception("Redis down"))

            result = await health_check(db=db)

        assert result.status == "degraded"
        assert result.redis == "error"

    @pytest.mark.asyncio
    async def test_degraded_when_both_fail(self):
        """Should return degraded when both DB and Redis fail."""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB down"))

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(side_effect=Exception("Redis down"))

            result = await health_check(db=db)

        assert result.status == "degraded"
        assert result.database == "error"
        assert result.redis == "error"


# ---------------------------------------------------------------------------
# get_rate_limit_dashboard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRateLimitDashboard:
    @pytest.mark.asyncio
    async def test_returns_dashboard_with_active_limits(self):
        """Should parse rate limit keys and return dashboard."""
        admin = _make_admin_user()

        mock_redis = AsyncMock()

        # Simulate scan_iter yielding rate limit keys
        async def mock_scan_iter(*args, **kwargs):
            yield b"rate_limit:auth:user_123"
            yield b"rate_limit:market_data:user_456"

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.get = AsyncMock(side_effect=[b"50", b"80"])
        mock_redis.ttl = AsyncMock(return_value=30)

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(return_value=mock_redis)

            result = await get_rate_limit_dashboard(current_user=admin)

        assert result.total_requests_last_hour == 130
        assert len(result.current_active_limits) == 2
        assert len(result.top_clients) == 2
        assert len(result.top_endpoints) == 2

    @pytest.mark.asyncio
    async def test_handles_empty_keys(self):
        """Should return empty dashboard when no rate limit keys exist."""
        admin = _make_admin_user()

        mock_redis = AsyncMock()

        async def mock_scan_iter(*args, **kwargs):
            return
            yield  # make it an async generator

        mock_redis.scan_iter = mock_scan_iter

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(return_value=mock_redis)

            result = await get_rate_limit_dashboard(current_user=admin)

        assert result.total_requests_last_hour == 0
        assert result.current_active_limits == []

    @pytest.mark.asyncio
    async def test_handles_malformed_keys(self):
        """Should skip keys that don't have expected format."""
        admin = _make_admin_user()

        mock_redis = AsyncMock()

        async def mock_scan_iter(*args, **kwargs):
            yield b"rate_limit:short"  # Only 2 parts, need 3
            yield b"rate_limit:auth:user_123"  # Valid

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.get = AsyncMock(return_value=b"10")
        mock_redis.ttl = AsyncMock(return_value=60)

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(return_value=mock_redis)

            result = await get_rate_limit_dashboard(current_user=admin)

        # Should only have 1 valid entry
        assert len(result.current_active_limits) == 1

    @pytest.mark.asyncio
    async def test_handles_null_count(self):
        """Should skip keys with null count."""
        admin = _make_admin_user()

        mock_redis = AsyncMock()

        async def mock_scan_iter(*args, **kwargs):
            yield b"rate_limit:auth:user_123"

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(return_value=mock_redis)

            result = await get_rate_limit_dashboard(current_user=admin)

        assert result.total_requests_last_hour == 0

    @pytest.mark.asyncio
    async def test_identifies_blocked_clients(self):
        """Should flag clients at or over limit as blocked."""
        admin = _make_admin_user()

        mock_redis = AsyncMock()

        async def mock_scan_iter(*args, **kwargs):
            yield b"rate_limit:auth:user_blocked"

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.get = AsyncMock(return_value=b"100")  # At limit (100)
        mock_redis.ttl = AsyncMock(return_value=30)

        with patch("app.api.v1.monitoring.rate_limit_service") as mock_rls:
            mock_rls.get_redis = AsyncMock(return_value=mock_redis)

            result = await get_rate_limit_dashboard(current_user=admin)

        assert result.blocked_requests_last_hour == 1
        assert result.current_active_limits[0].blocked is True


# ---------------------------------------------------------------------------
# get_system_stats
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSystemStats:
    @pytest.mark.asyncio
    async def test_returns_stats(self):
        """Should return user, account, and transaction counts."""
        admin = _make_admin_user()
        db = AsyncMock()

        # Mock 5 sequential execute calls
        results = [
            MagicMock(scalar=MagicMock(return_value=10)),  # users
            MagicMock(scalar=MagicMock(return_value=25)),  # accounts
            MagicMock(scalar=MagicMock(return_value=1000)),  # transactions
            MagicMock(scalar=MagicMock(return_value=2)),  # new users 24h
            MagicMock(scalar=MagicMock(return_value=50)),  # new transactions 24h
        ]
        db.execute = AsyncMock(side_effect=results)

        result = await get_system_stats(db=db, current_user=admin)

        assert "totals" in result
        assert "last_24_hours" in result
        assert "timestamp" in result
        assert result["totals"]["users"] == 10
        assert result["totals"]["accounts"] == 25
        assert result["totals"]["transactions"] == 1000


# ---------------------------------------------------------------------------
# get_circuit_breaker_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCircuitBreakerStatus:
    @pytest.mark.asyncio
    async def test_returns_circuit_breaker_status(self):
        """Should return circuit breaker states."""
        admin = _make_admin_user()

        mock_statuses = {
            "plaid": {"state": "closed", "failures": 0},
            "teller": {"state": "open", "failures": 5},
        }

        with patch("app.api.v1.monitoring.get_circuit_breaker") as mock_cb:
            mock_cb.return_value.get_all_statuses = AsyncMock(return_value=mock_statuses)

            result = await get_circuit_breaker_status(current_user=admin)

        assert "circuit_breakers" in result
        assert result["circuit_breakers"]["plaid"]["state"] == "closed"
        assert result["circuit_breakers"]["teller"]["state"] == "open"
        assert "timestamp" in result


# ---------------------------------------------------------------------------
# list_data_processing_activities
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDataProcessingActivities:
    @pytest.mark.asyncio
    async def test_returns_ropa(self):
        """Should return GDPR Article 30 records."""
        admin = _make_admin_user()

        result = await list_data_processing_activities(_admin=admin)

        assert "version" in result
        assert "activities" in result
        assert len(result["activities"]) == len(_ROPA)
        assert result["controller"] == "Nest Egg"


# ---------------------------------------------------------------------------
# get_active_jobs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetActiveJobs:
    @pytest.mark.asyncio
    async def test_returns_active_jobs(self):
        """Should return active, reserved, and scheduled Celery tasks."""
        admin = _make_admin_user()

        with patch("app.api.v1.monitoring.celery_app") as mock_celery:
            mock_inspector = MagicMock()
            mock_inspector.active.return_value = {
                "worker1": [{"id": "task_1", "name": "enrich", "time_start": 123, "args": []}]
            }
            mock_inspector.reserved.return_value = {
                "worker1": [{"id": "task_2", "name": "snapshot", "args": []}]
            }
            mock_inspector.scheduled.return_value = {
                "worker1": [
                    {
                        "request": {"id": "task_3", "name": "prices", "args": []},
                        "eta": "2024-06-15T18:00",
                    }
                ]
            }
            mock_celery.control.inspect.return_value = mock_inspector

            result = await get_active_jobs(current_user=admin)

        assert result["status"] == "ok"
        assert result["total"] == 3
        assert len(result["jobs"]) == 3

        # Check states
        states = [j["state"] for j in result["jobs"]]
        assert "ACTIVE" in states
        assert "RESERVED" in states
        assert "SCHEDULED" in states

    @pytest.mark.asyncio
    async def test_returns_unavailable_when_workers_offline(self):
        """Should return unavailable status when Celery workers can't be reached."""
        admin = _make_admin_user()

        with patch("app.api.v1.monitoring.celery_app") as mock_celery:
            mock_inspector = MagicMock()
            mock_inspector.active.side_effect = Exception("Connection refused")
            mock_celery.control.inspect.return_value = mock_inspector

            result = await get_active_jobs(current_user=admin)

        assert result["status"] == "unavailable"
        assert result["jobs"] == []


# ---------------------------------------------------------------------------
# get_job_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetJobStatus:
    @pytest.mark.asyncio
    async def test_returns_success_job(self):
        """Should return SUCCESS state with result."""
        admin = _make_admin_user()

        with patch("app.api.v1.monitoring.AsyncResult") as mock_ar:
            mock_result = MagicMock()
            mock_result.state = "SUCCESS"
            mock_result.result = {"updated": 10}
            mock_result.date_done = MagicMock()
            mock_result.date_done.isoformat.return_value = "2024-06-15T18:00:00"
            mock_ar.return_value = mock_result

            result = await get_job_status(task_id="task_123", current_user=admin)

        assert result["state"] == "SUCCESS"
        assert result["result"] == {"updated": 10}

    @pytest.mark.asyncio
    async def test_returns_failure_job(self):
        """Should return FAILURE state with error info."""
        admin = _make_admin_user()

        with patch("app.api.v1.monitoring.AsyncResult") as mock_ar:
            mock_result = MagicMock()
            mock_result.state = "FAILURE"
            mock_result.result = RuntimeError("Task crashed")
            mock_result.traceback = "Traceback ..."
            mock_result.date_done = None
            mock_ar.return_value = mock_result

            result = await get_job_status(task_id="task_fail", current_user=admin)

        assert result["state"] == "FAILURE"
        assert "Task crashed" in result["error"]
        assert result["traceback"] == "Traceback ..."

    @pytest.mark.asyncio
    async def test_returns_started_job(self):
        """Should return STARTED state with info."""
        admin = _make_admin_user()

        with patch("app.api.v1.monitoring.AsyncResult") as mock_ar:
            mock_result = MagicMock()
            mock_result.state = "STARTED"
            mock_result.info = {"progress": 50}
            mock_result.date_done = None
            mock_ar.return_value = mock_result

            result = await get_job_status(task_id="task_running", current_user=admin)

        assert result["state"] == "STARTED"
        assert result["info"] == {"progress": 50}

    @pytest.mark.asyncio
    async def test_returns_pending_job(self):
        """Should return PENDING state (default for unknown tasks)."""
        admin = _make_admin_user()

        with patch("app.api.v1.monitoring.AsyncResult") as mock_ar:
            mock_result = MagicMock()
            mock_result.state = "PENDING"
            mock_result.date_done = None
            mock_ar.return_value = mock_result

            result = await get_job_status(task_id="task_unknown", current_user=admin)

        assert result["state"] == "PENDING"
        assert result["date_done"] is None
