"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

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
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.CELERY_BROKER_URL,
    # Lock TTL: 5× the shortest schedule interval (1-minute check-budget runs at most hourly)
    redbeat_lock_timeout=300,
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


# Import tasks here as they're created
from app.workers.tasks import (
    auth_tasks,  # noqa: F401
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
    snapshot_tasks,  # noqa: F401
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
}
