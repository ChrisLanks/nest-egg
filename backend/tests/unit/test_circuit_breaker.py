"""Unit tests for CircuitBreaker — state transitions, Redis-backed logic, graceful degradation."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.circuit_breaker import (
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_FAILURE_THRESHOLD,
    DEFAULT_HALF_OPEN_SUCCESSES,
    CircuitBreaker,
    CircuitOpenError,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_redis_mock(state="closed", failures=0, last_failure=None, half_open_ok=0):
    """Build an AsyncMock Redis client with a small in-memory store."""
    store = {
        "cb:test_svc:state": state,
        "cb:test_svc:failures": str(failures),
        "cb:test_svc:half_open_ok": str(half_open_ok),
    }
    if last_failure:
        store["cb:test_svc:last_failure"] = last_failure

    r = AsyncMock()

    async def _get(key):
        return store.get(key)

    async def _set(key, value):
        store[key] = str(value)

    async def _incr(key):
        store[key] = str(int(store.get(key, "0")) + 1)
        return int(store[key])

    async def _delete(key):
        store.pop(key, None)

    r.get = AsyncMock(side_effect=_get)
    r.set = AsyncMock(side_effect=_set)
    r.incr = AsyncMock(side_effect=_incr)
    r.delete = AsyncMock(side_effect=_delete)

    # Pipeline mock — record calls and execute them against the store
    def _pipeline():
        pipe = MagicMock()
        ops = []

        def pipe_incr(key):
            ops.append(("incr", key))
            return pipe

        def pipe_set(key, value):
            ops.append(("set", key, value))
            return pipe

        def pipe_delete(key):
            ops.append(("delete", key))
            return pipe

        async def pipe_execute():
            results = []
            for op in ops:
                if op[0] == "incr":
                    store[op[1]] = str(int(store.get(op[1], "0")) + 1)
                    results.append(int(store[op[1]]))
                elif op[0] == "set":
                    store[op[1]] = str(op[2])
                    results.append(True)
                elif op[0] == "delete":
                    store.pop(op[1], None)
                    results.append(True)
            return results

        pipe.incr = MagicMock(side_effect=pipe_incr)
        pipe.set = MagicMock(side_effect=pipe_set)
        pipe.delete = MagicMock(side_effect=pipe_delete)
        pipe.execute = AsyncMock(side_effect=pipe_execute)
        return pipe

    r.pipeline = _pipeline
    r._store = store  # expose for assertions
    return r


def _make_cb(redis_mock, **kwargs):
    """Create a CircuitBreaker with an injected Redis mock."""
    cb = CircuitBreaker(**kwargs)
    cb._redis = redis_mock
    return cb


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCircuitBreakerInit:
    def test_default_values(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == DEFAULT_FAILURE_THRESHOLD
        assert cb.cooldown_seconds == DEFAULT_COOLDOWN_SECONDS
        assert cb.half_open_successes == DEFAULT_HALF_OPEN_SUCCESSES

    def test_custom_values(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=30, half_open_successes=1)
        assert cb.failure_threshold == 3
        assert cb.cooldown_seconds == 30
        assert cb.half_open_successes == 1

    def test_redis_starts_none(self):
        cb = CircuitBreaker()
        assert cb._redis is None


@pytest.mark.unit
class TestKeyHelper:
    def test_key_format(self):
        assert CircuitBreaker._key("plaid", "state") == "cb:plaid:state"

    def test_key_with_different_service(self):
        assert CircuitBreaker._key("teller", "failures") == "cb:teller:failures"

    def test_key_all_suffixes(self):
        for suffix in ("state", "failures", "last_failure", "half_open_ok"):
            key = CircuitBreaker._key("mx", suffix)
            assert key == f"cb:mx:{suffix}"


@pytest.mark.unit
class TestCallClosedState:
    @pytest.mark.asyncio
    async def test_success_returns_result(self):
        r = _make_redis_mock(state="closed")
        cb = _make_cb(r)
        func = AsyncMock(return_value={"accounts": [1, 2]})

        result = await cb.call("test_svc", func)

        assert result == {"accounts": [1, 2]}
        func.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success_resets_failure_counter(self):
        r = _make_redis_mock(state="closed", failures=2)
        cb = _make_cb(r)
        func = AsyncMock(return_value="ok")

        await cb.call("test_svc", func)

        # _record_success for closed state sets failures to 0
        assert r._store["cb:test_svc:failures"] == "0"

    @pytest.mark.asyncio
    async def test_failure_increments_counter(self):
        r = _make_redis_mock(state="closed", failures=0)
        cb = _make_cb(r)
        func = AsyncMock(side_effect=ConnectionError("timeout"))

        with pytest.raises(ConnectionError, match="timeout"):
            await cb.call("test_svc", func)

        assert int(r._store["cb:test_svc:failures"]) == 1

    @pytest.mark.asyncio
    async def test_failure_records_timestamp(self):
        r = _make_redis_mock(state="closed", failures=0)
        cb = _make_cb(r)
        func = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError):
            await cb.call("test_svc", func)

        assert "cb:test_svc:last_failure" in r._store

    @pytest.mark.asyncio
    async def test_args_forwarded_to_func(self):
        r = _make_redis_mock(state="closed")
        cb = _make_cb(r)
        func = AsyncMock(return_value="ok")

        await cb.call("test_svc", func, "arg1", key="val")

        func.assert_awaited_once_with("arg1", key="val")


@pytest.mark.unit
class TestCallOpenState:
    @pytest.mark.asyncio
    async def test_raises_circuit_open_error(self):
        r = _make_redis_mock(state="open", last_failure="2099-01-01T00:00:00+00:00")
        cb = _make_cb(r, cooldown_seconds=9999)

        func = AsyncMock()
        with pytest.raises(CircuitOpenError) as exc_info:
            await cb.call("test_svc", func)

        assert exc_info.value.service_name == "test_svc"
        func.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_cooldown(self):
        # last_failure far in the past → cooldown elapsed
        r = _make_redis_mock(state="open", last_failure="2000-01-01T00:00:00+00:00")
        cb = _make_cb(r, cooldown_seconds=1)
        func = AsyncMock(return_value="recovered")

        result = await cb.call("test_svc", func)

        assert result == "recovered"
        func.assert_awaited_once()


@pytest.mark.unit
class TestClosedToOpenTransition:
    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        threshold = 3
        r = _make_redis_mock(state="closed", failures=0)
        cb = _make_cb(r, failure_threshold=threshold)

        func = AsyncMock(side_effect=RuntimeError("fail"))

        for _ in range(threshold):
            with pytest.raises(RuntimeError):
                await cb.call("test_svc", func)

        # After threshold failures the state should be open
        assert r._store["cb:test_svc:state"] == "open"

    @pytest.mark.asyncio
    async def test_stays_closed_below_threshold(self):
        threshold = 3
        r = _make_redis_mock(state="closed", failures=0)
        cb = _make_cb(r, failure_threshold=threshold)

        func = AsyncMock(side_effect=RuntimeError("fail"))

        for _ in range(threshold - 1):
            with pytest.raises(RuntimeError):
                await cb.call("test_svc", func)

        assert r._store["cb:test_svc:state"] == "closed"


@pytest.mark.unit
class TestCallHalfOpenState:
    @pytest.mark.asyncio
    async def test_success_increments_probe_counter(self):
        r = _make_redis_mock(state="half_open", half_open_ok=0)
        cb = _make_cb(r, half_open_successes=3)
        func = AsyncMock(return_value="ok")

        await cb.call("test_svc", func)

        assert int(r._store["cb:test_svc:half_open_ok"]) == 1
        # Not enough successes yet — still half_open
        assert r._store["cb:test_svc:state"] == "half_open"

    @pytest.mark.asyncio
    async def test_enough_successes_transitions_to_closed(self):
        required = 2
        r = _make_redis_mock(state="half_open", half_open_ok=0)
        cb = _make_cb(r, half_open_successes=required)
        func = AsyncMock(return_value="ok")

        for _ in range(required):
            await cb.call("test_svc", func)

        assert r._store["cb:test_svc:state"] == "closed"
        assert int(r._store["cb:test_svc:failures"]) == 0

    @pytest.mark.asyncio
    async def test_failure_reopens_circuit(self):
        r = _make_redis_mock(state="half_open", half_open_ok=1)
        cb = _make_cb(r, half_open_successes=3)
        func = AsyncMock(side_effect=RuntimeError("still broken"))

        with pytest.raises(RuntimeError):
            await cb.call("test_svc", func)

        assert r._store["cb:test_svc:state"] == "open"


@pytest.mark.unit
class TestGetServiceStatus:
    @pytest.mark.asyncio
    async def test_returns_correct_status_dict(self):
        r = _make_redis_mock(state="closed", failures=2, last_failure="2025-06-01T12:00:00+00:00")
        cb = _make_cb(r, failure_threshold=5, cooldown_seconds=60)

        status = await cb.get_service_status("test_svc")

        assert status["service"] == "test_svc"
        assert status["state"] == "closed"
        assert status["failures"] == 2
        assert status["last_failure"] == "2025-06-01T12:00:00+00:00"
        assert status["failure_threshold"] == 5
        assert status["cooldown_seconds"] == 60

    @pytest.mark.asyncio
    async def test_open_with_elapsed_cooldown_reports_half_open(self):
        r = _make_redis_mock(state="open", last_failure="2000-01-01T00:00:00+00:00")
        cb = _make_cb(r, cooldown_seconds=1)

        status = await cb.get_service_status("test_svc")

        assert status["state"] == "half_open"

    @pytest.mark.asyncio
    async def test_defaults_when_no_failures(self):
        r = _make_redis_mock(state="closed", failures=0)
        cb = _make_cb(r)

        status = await cb.get_service_status("test_svc")

        assert status["failures"] == 0
        assert status["last_failure"] is None


@pytest.mark.unit
class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_executes_directly_when_redis_unavailable(self):
        cb = CircuitBreaker()
        # _get_redis raises when trying to connect
        cb._get_redis = AsyncMock(side_effect=ConnectionError("Redis down"))

        func = AsyncMock(return_value="direct_result")
        result = await cb.call("test_svc", func)

        assert result == "direct_result"
        func.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_status_returns_unknown_when_redis_unavailable(self):
        cb = CircuitBreaker()
        cb._get_redis = AsyncMock(side_effect=ConnectionError("Redis down"))

        status = await cb.get_service_status("plaid")

        assert status["state"] == "unknown"
        assert status["error"] == "Redis unavailable"
        assert status["service"] == "plaid"
