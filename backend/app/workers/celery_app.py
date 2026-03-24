"""Celery application configuration."""

import logging

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "nest-egg",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=270,  # 4.5 minutes soft limit
    # Reliability: re-queue tasks if a worker crashes mid-execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 60 seconds base delay before first retry
    # Distributed beat scheduler: prevents multiple beat workers from firing the
    # same task when scaled horizontally. RedBeat uses Redis as a distributed lock
    # so only one beat process runs each task at its scheduled time.
    # Uses our ResilientRedBeatScheduler subclass (defined below) that re-acquires
    # the lock when it expires due to container freeze / GC pause (LockNotOwnedError).
    beat_scheduler="app.workers.celery_app.ResilientRedBeatScheduler",
    redbeat_redis_url=settings.CELERY_BROKER_URL,
    # Lock TTL must exceed task_time_limit to prevent LockNotOwnedError.
    # If the lock expires while the beat scheduling cycle is still running,
    # Redis raises LockNotOwnedError when beat tries to extend/release the lock.
    # Set to task_time_limit (300s) + 60s buffer = 360s.
    redbeat_lock_timeout=360,
    # Suppress CPendingDeprecationWarning in Celery 5.x: explicitly opt in to
    # retrying broker connections on startup (behaviour unchanged from before).
    broker_connection_retry_on_startup=True,
    # Auto-expire task results in Redis after 1 hour to prevent unbounded growth.
    result_expires=3600,
)


class RetryableTask(celery_app.Task):
    """
    Base task class with automatic exponential-backoff retry on failure.

    All periodic and background tasks inherit this so transient errors
    (DB timeouts, network blips, API rate limits) are handled automatically.
    Override max_retries=0 on tasks that must not retry (e.g., send-once emails).
    """

    abstract = True
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True  # Exponential: 60s → 120s → 240s
    retry_backoff_max = 600  # Cap at 10 minutes
    retry_jitter = True  # Add jitter to prevent thundering herd on retry wave


celery_app.Task = RetryableTask


class ResilientRedBeatScheduler:
    """
    RedBeat scheduler subclass that survives LockNotOwnedError.

    When a container is frozen (OOM pause, live-migration, GC stop-the-world)
    the beat process can be suspended for longer than redbeat_lock_timeout.
    Redis expires the distributed lock while beat is paused; on resume,
    self.lock.extend() raises LockNotOwnedError and Celery beat crashes.

    This subclass catches LockNotOwnedError in tick(), re-acquires the lock,
    and continues scheduling without restarting the beat process.
    """

    # Defined as a lazy import wrapper so the class is only resolved when
    # celery-beat actually starts — avoids importing redbeat at import time
    # (which would fail in environments without Redis).
    _scheduler_cls = None

    def __new__(cls, *args, **kwargs):
        # Resolve the real scheduler class on first instantiation
        from redbeat.schedulers import RedBeatScheduler, get_redis

        class _Impl(RedBeatScheduler):
            def tick(self, min=min, **kwargs):  # type: ignore[override]
                if self.lock_key and self.lock is not None:
                    try:
                        self.lock.extend(int(self.lock_timeout))
                    except Exception as exc:
                        # LockNotOwnedError: lock expired while beat was paused.
                        # Re-acquire and continue — do NOT crash.
                        logger.warning(
                            "beat: Lost distributed lock (%s). Re-acquiring...", exc
                        )
                        try:
                            redis_client = get_redis(self.app)
                            new_lock = redis_client.lock(
                                self.lock_key,
                                timeout=self.lock_timeout,
                                sleep=0.1,
                            )
                            new_lock.acquire(blocking=True, blocking_timeout=5)
                            self.lock = new_lock
                            logger.info("beat: Re-acquired distributed lock.")
                        except Exception as reacquire_exc:
                            logger.error(
                                "beat: Failed to re-acquire lock: %s. "
                                "Skipping this tick to avoid duplicate task firing.",
                                reacquire_exc,
                            )
                            return self.max_interval

                remaining_times = []
                try:
                    for entry in self.schedule.values():
                        next_time_to_run = self.maybe_due(entry, **self._maybe_due_kwargs)
                        if next_time_to_run:
                            remaining_times.append(next_time_to_run)
                except RuntimeError:
                    pass

                return min(remaining_times + [self.max_interval])

        return _Impl(*args, **kwargs)


# Import tasks here as they're created
from app.workers.tasks import (
    auth_tasks,  # noqa: F401
    bill_reminder_tasks,  # noqa: F401
    budget_tasks,  # noqa: F401
    forecast_tasks,  # noqa: F401
    guest_access_tasks,  # noqa: F401
    holdings_tasks,  # noqa: F401
    interest_accrual_tasks,  # noqa: F401
    recap_tasks,  # noqa: F401
    recurring_tasks,  # noqa: F401
    report_tasks,  # noqa: F401
    retention_tasks,  # noqa: F401
    retirement_tasks,  # noqa: F401
    scf_benchmark_tasks,  # noqa: F401
    snapshot_tasks,  # noqa: F401
    suggestion_tasks,  # noqa: F401
)

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    "cleanup-expired-refresh-tokens": {
        "task": "cleanup_expired_refresh_tokens",
        "schedule": crontab(hour=3, minute=0),  # 3am daily
    },
    "check-budget-alerts-daily": {
        "task": "check_budget_alerts",
        "schedule": crontab(hour=0, minute=0),  # Midnight daily
    },
    "detect-recurring-patterns": {
        "task": "detect_recurring_patterns",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # Monday 2am
    },
    "check-cash-flow-forecast": {
        "task": "check_cash_flow_forecast",
        "schedule": crontab(hour=6, minute=30),  # 6:30am daily
    },
    "update-holdings-prices": {
        "task": "update_holdings_prices",
        "schedule": crontab(hour=18, minute=0),  # 6:00 PM EST daily (after market close)
    },
    "enrich-holdings-metadata": {
        "task": "enrich_holdings_metadata",
        "schedule": crontab(hour=19, minute=0),  # 7:00 PM EST daily (after price update)
    },
    "capture-daily-holdings-snapshot": {
        "task": "capture_daily_holdings_snapshot",
        "schedule": crontab(hour=23, minute=59),  # 11:59 PM daily to capture end-of-day values
    },
    "accrue-account-interest": {
        "task": "accrue_account_interest",
        "schedule": crontab(hour=1, minute=0, day_of_month=1),  # 1am on 1st of each month
    },
    # Portfolio net-worth snapshots (replaces in-process SnapshotScheduler loop)
    "orchestrate-portfolio-snapshots": {
        "task": "orchestrate_portfolio_snapshots",
        "schedule": crontab(hour=0, minute=0),  # Midnight UTC — tasks stagger themselves
    },
    # Auth token cleanup (replaces SnapshotScheduler.run_cleanup_loop)
    "cleanup-expired-auth-tokens": {
        "task": "cleanup_expired_auth_tokens",
        "schedule": crontab(hour=4, minute=0),  # 4am daily
    },
    # Data retention — only effective when DATA_RETENTION_DAYS is set
    "run-data-retention": {
        "task": "run_data_retention",
        "schedule": crontab(hour=3, minute=30),  # 3:30am daily
    },
    # Cleanup archived retirement scenarios with no active members
    "cleanup-archived-retirement-scenarios": {
        "task": "cleanup_archived_retirement_scenarios",
        "schedule": crontab(hour=4, minute=30),  # 4:30am daily
    },
    # Weekly financial recap — every Monday 8am UTC
    "send-weekly-recaps": {
        "task": "send_weekly_recaps",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
    # Auto-revoke guest access records past their expires_at date
    "auto-revoke-expired-guests": {
        "task": "auto_revoke_expired_guests",
        "schedule": crontab(hour=2, minute=0),  # 2am daily
    },
    # Scheduled report delivery — templates with scheduled_delivery.enabled=true
    "send-scheduled-reports": {
        "task": "send_scheduled_reports",
        "schedule": crontab(hour=8, minute=0),  # 8am daily
    },
    # Bill payment reminders — notify users of upcoming/overdue bills
    "send-bill-reminders": {
        "task": "send_bill_reminders",
        "schedule": crontab(hour=8, minute=0),  # 8am daily
    },
    # Pre-compute budget suggestions for all orgs — 2:05am daily
    # (after recurring pattern detection at 2am, so categories are up-to-date)
    "refresh-budget-suggestions": {
        "task": "refresh_budget_suggestions",
        "schedule": crontab(hour=2, minute=5),
    },
    # Refresh SCF net-worth benchmark data annually (Jan 1 5am UTC).
    # Only scrapes when data is stale (>3 years old); otherwise no-ops.
    # Falls back gracefully to static table in financial.py on failure.
    "refresh-scf-benchmarks": {
        "task": "refresh_scf_benchmarks",
        "schedule": crontab(hour=5, minute=0, month_of_year=1, day_of_month=1),
    },
}
