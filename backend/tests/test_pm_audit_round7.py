"""Tests for PM audit round 7 fixes.

Covers:
- redbeat_lock_timeout > task_time_limit (LockNotOwnedError prevention)
- Celery beat config sanity checks
"""

import pytest


def test_redbeat_lock_timeout_exceeds_task_time_limit():
    """redbeat_lock_timeout must be strictly greater than task_time_limit.

    If lock_timeout == task_time_limit, a task that runs to the limit can cause
    the beat lock to expire, and Redis raises LockNotOwnedError when beat tries
    to extend/release it. We require at least a 60-second buffer.
    """
    from app.workers.celery_app import celery_app

    conf = celery_app.conf
    lock_timeout = conf.redbeat_lock_timeout
    task_time_limit = conf.task_time_limit

    assert lock_timeout is not None, "redbeat_lock_timeout must be set"
    assert task_time_limit is not None, "task_time_limit must be set"
    assert lock_timeout > task_time_limit, (
        f"redbeat_lock_timeout ({lock_timeout}s) must exceed "
        f"task_time_limit ({task_time_limit}s) to prevent LockNotOwnedError"
    )
    # Require at least 60s buffer
    assert lock_timeout >= task_time_limit + 60, (
        f"redbeat_lock_timeout ({lock_timeout}s) should be at least "
        f"task_time_limit + 60s ({task_time_limit + 60}s)"
    )


def test_redbeat_lock_timeout_value():
    """redbeat_lock_timeout should be 360 (300 task limit + 60s buffer)."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.redbeat_lock_timeout == 360


def test_task_time_limit_value():
    """task_time_limit should remain at 300s (5 minutes)."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.task_time_limit == 300


def test_task_soft_time_limit_less_than_hard_limit():
    """soft time limit must be less than hard limit to allow graceful shutdown."""
    from app.workers.celery_app import celery_app

    conf = celery_app.conf
    assert conf.task_soft_time_limit < conf.task_time_limit, (
        "task_soft_time_limit must be less than task_time_limit"
    )


def test_broker_connection_retry_on_startup():
    """broker_connection_retry_on_startup must be True to suppress deprecation warning."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.broker_connection_retry_on_startup is True


def test_task_acks_late_enabled():
    """task_acks_late must be True for reliable task delivery on worker crash."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.task_acks_late is True


def test_beat_scheduler_is_redbeat():
    """beat_scheduler must be RedBeatScheduler (or a subclass) for distributed locking."""
    from app.workers.celery_app import celery_app

    scheduler = celery_app.conf.beat_scheduler
    assert "RedBeat" in scheduler, (
        f"beat_scheduler must be a RedBeat variant, got {scheduler!r}"
    )


def test_retryable_task_has_jitter():
    """RetryableTask must have jitter enabled to prevent thundering herd on retries."""
    from app.workers.celery_app import RetryableTask

    assert RetryableTask.retry_jitter is True


def test_retryable_task_backoff_cap():
    """RetryableTask backoff cap must be at least 10 minutes."""
    from app.workers.celery_app import RetryableTask

    assert RetryableTask.retry_backoff_max >= 600


def test_retryable_task_max_retries():
    """RetryableTask max_retries should be 3 (reasonable for transient errors)."""
    from app.workers.celery_app import RetryableTask

    assert RetryableTask.max_retries == 3


def test_all_beat_tasks_have_schedule():
    """Every entry in beat_schedule must have both 'task' and 'schedule' keys."""
    from app.workers.celery_app import celery_app

    for name, entry in celery_app.conf.beat_schedule.items():
        assert "task" in entry, f"Beat entry '{name}' missing 'task' key"
        assert "schedule" in entry, f"Beat entry '{name}' missing 'schedule' key"
        assert entry["task"], f"Beat entry '{name}' has empty task name"
