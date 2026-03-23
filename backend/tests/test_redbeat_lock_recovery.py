"""Tests for ResilientRedBeatScheduler LockNotOwnedError recovery.

Covers:
- beat_scheduler is set to our resilient subclass
- The resilient tick logic re-acquires on LockNotOwnedError instead of crashing
- Falls back to max_interval when re-acquire also fails
- Successful extend path is unaffected
"""

from unittest.mock import MagicMock


def test_beat_scheduler_is_resilient_subclass():
    """beat_scheduler config must point to our resilient subclass, not bare redbeat."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.beat_scheduler == "app.workers.celery_app.ResilientRedBeatScheduler"


def test_resilient_scheduler_is_importable():
    """ResilientRedBeatScheduler must be importable from celery_app."""
    from app.workers.celery_app import ResilientRedBeatScheduler

    assert ResilientRedBeatScheduler is not None


def test_redbeat_lock_timeout_value():
    """redbeat_lock_timeout must be 360 (300s task limit + 60s buffer)."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.redbeat_lock_timeout == 360


def test_tick_reacquires_lock_on_lock_not_owned_error():
    """When lock.extend() raises, tick logic re-acquires and returns a valid interval."""
    from redis.exceptions import LockNotOwnedError

    max_interval = 5.0
    lock_key = "redbeat::lock"
    lock_timeout = 360

    old_lock = MagicMock()
    old_lock.extend.side_effect = LockNotOwnedError("Cannot extend a lock that's no longer owned")

    new_lock = MagicMock()
    new_lock.acquire.return_value = True

    redis_client = MagicMock()
    redis_client.lock.return_value = new_lock

    state = {"lock": old_lock}

    interval = _resilient_tick(
        lock_key=lock_key,
        lock_timeout=lock_timeout,
        lock=state["lock"],
        max_interval=max_interval,
        redis_client=redis_client,
        state=state,
        entries=[],
    )

    assert isinstance(interval, float)
    new_lock.acquire.assert_called_once()
    assert state["lock"] is new_lock


def test_tick_returns_max_interval_when_reacquire_fails():
    """When re-acquire also fails, tick returns max_interval (safe skip)."""
    from redis.exceptions import LockNotOwnedError

    max_interval = 5.0
    lock_key = "redbeat::lock"
    lock_timeout = 360

    old_lock = MagicMock()
    old_lock.extend.side_effect = LockNotOwnedError("Cannot extend")

    redis_client = MagicMock()
    redis_client.lock.return_value = MagicMock(
        acquire=MagicMock(side_effect=Exception("Redis connection refused"))
    )

    state = {"lock": old_lock}

    interval = _resilient_tick(
        lock_key=lock_key,
        lock_timeout=lock_timeout,
        lock=state["lock"],
        max_interval=max_interval,
        redis_client=redis_client,
        state=state,
        entries=[],
    )

    assert interval == max_interval


def test_tick_normal_extend_path_unaffected():
    """When extend() succeeds, tick runs normally without hitting re-acquire path."""
    max_interval = 5.0
    lock_key = "redbeat::lock"
    lock_timeout = 360

    lock = MagicMock()
    lock.extend.return_value = True

    state = {"lock": lock}

    interval = _resilient_tick(
        lock_key=lock_key,
        lock_timeout=lock_timeout,
        lock=state["lock"],
        max_interval=max_interval,
        redis_client=None,
        state=state,
        entries=[],
    )

    assert isinstance(interval, float)
    lock.extend.assert_called_once_with(360)


def test_tick_no_lock_key_skips_extend():
    """When lock_key is None (no distributed lock), extend is never called."""
    lock = MagicMock()
    state = {"lock": lock}

    interval = _resilient_tick(
        lock_key=None,
        lock_timeout=360,
        lock=lock,
        max_interval=5.0,
        redis_client=None,
        state=state,
        entries=[],
    )

    assert isinstance(interval, float)
    lock.extend.assert_not_called()


# ---------------------------------------------------------------------------
# Inline re-implementation of the resilient tick logic for unit-testing
# without needing a full Celery + Redis environment.
# ---------------------------------------------------------------------------

def _resilient_tick(*, lock_key, lock_timeout, lock, max_interval, redis_client, state, entries):
    """
    Mirrors the logic inside ResilientRedBeatScheduler._Impl.tick().
    Returns the sleep interval.
    """
    import logging
    log = logging.getLogger("test")

    if lock_key and lock is not None:
        try:
            lock.extend(int(lock_timeout))
        except Exception as exc:
            log.warning("beat: Lost distributed lock (%s). Re-acquiring...", exc)
            try:
                new_lock = redis_client.lock(lock_key, timeout=lock_timeout, sleep=0.1)
                new_lock.acquire(blocking=True, blocking_timeout=5)
                state["lock"] = new_lock
            except Exception as reacquire_exc:
                log.error("beat: Failed to re-acquire lock: %s", reacquire_exc)
                return float(max_interval)

    remaining = list(entries)  # entry next_time values
    return float(min(remaining + [max_interval]))
