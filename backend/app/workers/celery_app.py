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
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # 9 minutes soft limit
)

# Import tasks here as they're created
from app.workers.tasks import budget_tasks  # noqa: F401

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    'check-budget-alerts-daily': {
        'task': 'check_budget_alerts',
        'schedule': crontab(hour=0, minute=0),  # Midnight daily
    },
}
