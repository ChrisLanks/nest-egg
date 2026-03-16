"""Unit tests for anomaly detection middleware."""

from time import time
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.middleware.anomaly_detection import (
    AnomalyDetectionMiddleware,
    _export_counter,
    _forbidden_counter,
    _get_ip,
    _SlidingWindowCounter,
    _unauthorized_counter,
)

# ── _SlidingWindowCounter ────────────────────────────────────────────────────


@pytest.mark.unit
class TestSlidingWindowCounter:
    """Test the sliding window counter."""

    def test_record_below_threshold(self):
        counter = _SlidingWindowCounter(window_seconds=60, threshold=3, label="test")
        assert counter.record_and_check("key1") is False

    def test_record_reaches_threshold(self):
        counter = _SlidingWindowCounter(window_seconds=60, threshold=3, label="test")
        counter.record_and_check("key1")
        counter.record_and_check("key1")
        assert counter.record_and_check("key1") is True

    def test_different_keys_separate(self):
        counter = _SlidingWindowCounter(window_seconds=60, threshold=2, label="test")
        counter.record_and_check("key1")
        counter.record_and_check("key2")
        assert counter.record_and_check("key1") is True
        assert counter.count("key2") == 1

    def test_count_returns_current_events(self):
        counter = _SlidingWindowCounter(window_seconds=60, threshold=10, label="test")
        counter.record_and_check("key1")
        counter.record_and_check("key1")
        assert counter.count("key1") == 2

    def test_count_empty_key(self):
        counter = _SlidingWindowCounter(window_seconds=60, threshold=10, label="test")
        assert counter.count("nonexistent") == 0

    def test_cleanup_removes_expired_keys(self):
        counter = _SlidingWindowCounter(window_seconds=1, threshold=10, label="test")
        # Manually add expired events
        counter._events["old_key"] = [time() - 100]
        counter._events["fresh_key"] = [time()]
        counter.cleanup()
        assert "old_key" not in counter._events
        assert "fresh_key" in counter._events

    def test_periodic_cleanup_triggered(self):
        counter = _SlidingWindowCounter(window_seconds=60, threshold=1000, label="test")
        counter._ops_since_cleanup = 999
        counter.record_and_check("key1")
        assert counter._ops_since_cleanup == 0

    def test_expired_events_evicted(self):
        counter = _SlidingWindowCounter(window_seconds=1, threshold=10, label="test")
        # Add an event that's already expired
        counter._events["key1"] = [time() - 10]
        counter.record_and_check("key1")
        # After eviction and adding new one, should be 1
        assert counter.count("key1") == 1


# ── _get_ip ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetIp:
    """Test IP extraction from request."""

    def test_x_forwarded_for_single(self):
        request = Mock()
        request.headers = {"X-Forwarded-For": "1.2.3.4"}
        request.client = Mock(host="127.0.0.1")
        assert _get_ip(request) == "1.2.3.4"

    def test_x_forwarded_for_multiple_takes_first(self):
        request = Mock()
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}
        request.client = Mock(host="127.0.0.1")
        assert _get_ip(request) == "1.2.3.4"

    def test_no_forwarded_header_uses_client(self):
        request = Mock()
        request.headers = {}
        request.client = Mock(host="192.168.1.1")
        assert _get_ip(request) == "192.168.1.1"

    def test_no_client_returns_unknown(self):
        request = Mock()
        request.headers = {}
        request.client = None
        assert _get_ip(request) == "unknown"

    def test_empty_forwarded_header(self):
        request = Mock()
        request.headers = {"X-Forwarded-For": ""}
        request.client = Mock(host="10.0.0.1")
        assert _get_ip(request) == "10.0.0.1"


# ── AnomalyDetectionMiddleware ───────────────────────────────────────────────


@pytest.mark.unit
class TestAnomalyDetectionMiddleware:
    """Test the middleware dispatch logic."""

    @pytest.mark.asyncio
    async def test_normal_request_passes_through(self):
        """Non-error response passes through without alerts."""
        middleware = AnomalyDetectionMiddleware(app=Mock())
        request = Mock()
        request.headers = {}
        request.client = Mock(host="10.0.0.1")
        request.url = Mock(path="/api/v1/accounts")

        response = Mock()
        response.status_code = 200

        async def call_next(req):
            return response

        result = await middleware.dispatch(request, call_next)
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_403_recorded(self):
        """403 responses are tracked."""
        middleware = AnomalyDetectionMiddleware(app=Mock())
        request = Mock()
        request.headers = {}
        request.client = Mock(host="10.0.0.99")
        request.url = Mock(path="/api/v1/accounts")

        response = Mock()
        response.status_code = 403

        async def call_next(req):
            return response

        with patch.object(
            _forbidden_counter, "record_and_check", return_value=False
        ) as mock_record:
            await middleware.dispatch(request, call_next)
            mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_403_threshold_logs_critical(self):
        """Repeated 403s trigger CRITICAL log."""
        middleware = AnomalyDetectionMiddleware(app=Mock())
        request = Mock()
        request.headers = {}
        request.client = Mock(host="10.0.0.100")
        request.url = Mock(path="/api/v1/accounts")

        response = Mock()
        response.status_code = 403

        async def call_next(req):
            return response

        with (
            patch.object(_forbidden_counter, "record_and_check", return_value=True),
            patch.object(_forbidden_counter, "count", return_value=5),
            patch("app.middleware.anomaly_detection.logger") as mock_logger,
        ):
            await middleware.dispatch(request, call_next)
            mock_logger.critical.assert_called_once()

    @pytest.mark.asyncio
    async def test_401_recorded(self):
        """401 responses are tracked."""
        middleware = AnomalyDetectionMiddleware(app=Mock())
        request = Mock()
        request.headers = {}
        request.client = Mock(host="10.0.0.101")
        request.url = Mock(path="/api/v1/auth/login")

        response = Mock()
        response.status_code = 401

        async def call_next(req):
            return response

        with patch.object(
            _unauthorized_counter, "record_and_check", return_value=False
        ) as mock_record:
            await middleware.dispatch(request, call_next)
            mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_401_threshold_logs_critical(self):
        """Repeated 401s trigger CRITICAL log."""
        middleware = AnomalyDetectionMiddleware(app=Mock())
        request = Mock()
        request.headers = {}
        request.client = Mock(host="10.0.0.102")
        request.url = Mock(path="/api/v1/auth/login")

        response = Mock()
        response.status_code = 401

        async def call_next(req):
            return response

        with (
            patch.object(_unauthorized_counter, "record_and_check", return_value=True),
            patch.object(_unauthorized_counter, "count", return_value=10),
            patch("app.middleware.anomaly_detection.logger") as mock_logger,
        ):
            await middleware.dispatch(request, call_next)
            mock_logger.critical.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_path_tracked(self):
        """Successful export calls are tracked."""
        middleware = AnomalyDetectionMiddleware(app=Mock())
        request = Mock()
        request.headers = {}
        request.client = Mock(host="10.0.0.103")
        request.url = Mock(path="/api/v1/settings/export")
        request.state = Mock(user_id=uuid4())

        response = Mock()
        response.status_code = 200

        async def call_next(req):
            return response

        with patch.object(_export_counter, "record_and_check", return_value=False) as mock_record:
            await middleware.dispatch(request, call_next)
            mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_threshold_logs_critical(self):
        """Repeated exports trigger CRITICAL log."""
        middleware = AnomalyDetectionMiddleware(app=Mock())
        request = Mock()
        request.headers = {}
        request.client = Mock(host="10.0.0.104")
        request.url = Mock(path="/api/v1/settings/export")
        request.state = Mock(user_id=uuid4())

        response = Mock()
        response.status_code = 200

        async def call_next(req):
            return response

        with (
            patch.object(_export_counter, "record_and_check", return_value=True),
            patch.object(_export_counter, "count", return_value=3),
            patch("app.middleware.anomaly_detection.logger") as mock_logger,
        ):
            await middleware.dispatch(request, call_next)
            mock_logger.critical.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_no_user_id_uses_ip(self):
        """When no user_id in state, uses IP as key."""
        middleware = AnomalyDetectionMiddleware(app=Mock())
        request = Mock()
        request.headers = {}
        request.client = Mock(host="10.0.0.105")
        request.url = Mock(path="/api/v1/settings/export")
        request.state = Mock(spec=[])  # No user_id attribute

        response = Mock()
        response.status_code = 200

        async def call_next(req):
            return response

        with patch.object(_export_counter, "record_and_check", return_value=False) as mock_record:
            await middleware.dispatch(request, call_next)
            # Should use IP since user_id is not set
            call_key = mock_record.call_args[0][0]
            assert call_key == "10.0.0.105"
