"""
Tests for background sync tasks and storage auto-detection.

1. sync_plaid_transactions_task is registered in Celery
2. sync_teller_transactions_task is registered in Celery
3. sync_mx_transactions_task is registered in Celery
4. Plaid sync task retries up to 3 times
5. Teller sync task retries up to 3 times
6. MX sync task retries up to 3 times
7. Storage service auto-promotes to S3 when bucket is set
8. Storage service stays local when no bucket configured
9. Storage service raises when STORAGE_BACKEND=s3 but no bucket
10. Plaid sync task module importable (no circular imports)
11. Teller sync task module importable
12. MX sync task module importable
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Celery task registration
# ---------------------------------------------------------------------------


def test_plaid_sync_task_registered():
    """sync_plaid_transactions is registered as a Celery task."""
    from app.workers.tasks.sync_tasks import sync_plaid_transactions_task

    assert sync_plaid_transactions_task.name == "sync_plaid_transactions"


def test_teller_sync_task_registered():
    """sync_teller_transactions is registered as a Celery task."""
    from app.workers.tasks.sync_tasks import sync_teller_transactions_task

    assert sync_teller_transactions_task.name == "sync_teller_transactions"


def test_plaid_sync_task_max_retries():
    """Plaid sync task retries up to 3 times."""
    from app.workers.tasks.sync_tasks import sync_plaid_transactions_task

    assert sync_plaid_transactions_task.max_retries == 3


def test_teller_sync_task_max_retries():
    """Teller sync task retries up to 3 times."""
    from app.workers.tasks.sync_tasks import sync_teller_transactions_task

    assert sync_teller_transactions_task.max_retries == 3


def test_mx_sync_task_registered():
    """sync_mx_transactions is registered as a Celery task."""
    from app.workers.tasks.sync_tasks import sync_mx_transactions_task

    assert sync_mx_transactions_task.name == "sync_mx_transactions"


def test_mx_sync_task_max_retries():
    """MX sync task retries up to 3 times."""
    from app.workers.tasks.sync_tasks import sync_mx_transactions_task

    assert sync_mx_transactions_task.max_retries == 3


# ---------------------------------------------------------------------------
# Storage auto-detection
# ---------------------------------------------------------------------------


@patch("app.services.storage_service.settings")
def test_storage_auto_promotes_to_s3(mock_settings):
    """When AWS_S3_BUCKET is set, storage auto-promotes to S3 even if STORAGE_BACKEND=local."""
    from app.services.storage_service import S3StorageService, get_storage_service

    mock_settings.STORAGE_BACKEND = "local"
    mock_settings.AWS_S3_BUCKET = "my-bucket"
    mock_settings.AWS_REGION = "us-east-1"
    mock_settings.AWS_ACCESS_KEY_ID = None
    mock_settings.AWS_SECRET_ACCESS_KEY = None
    mock_settings.AWS_S3_PREFIX = "uploads/"

    service = get_storage_service()
    assert isinstance(service, S3StorageService)


@patch("app.services.storage_service.settings")
def test_storage_stays_local_when_no_bucket(mock_settings):
    """Without S3 bucket, storage stays local."""
    from app.services.storage_service import LocalStorageService, get_storage_service

    mock_settings.STORAGE_BACKEND = "local"
    mock_settings.AWS_S3_BUCKET = None
    mock_settings.LOCAL_UPLOAD_DIR = "./uploads"

    service = get_storage_service()
    assert isinstance(service, LocalStorageService)


@patch("app.services.storage_service.settings")
def test_storage_explicit_s3_without_bucket_raises(mock_settings):
    """Explicit STORAGE_BACKEND=s3 without bucket raises RuntimeError."""
    from app.services.storage_service import get_storage_service

    mock_settings.STORAGE_BACKEND = "s3"
    mock_settings.AWS_S3_BUCKET = None

    with pytest.raises(RuntimeError, match="AWS_S3_BUCKET"):
        get_storage_service()


# ---------------------------------------------------------------------------
# Webhook dispatch verification
# ---------------------------------------------------------------------------


def test_plaid_webhook_imports_sync_task():
    """The sync task module can be imported (no circular imports)."""
    from app.workers.tasks.sync_tasks import sync_plaid_transactions_task

    assert callable(sync_plaid_transactions_task.delay)


def test_teller_webhook_imports_sync_task():
    """The sync task module can be imported (no circular imports)."""
    from app.workers.tasks.sync_tasks import sync_teller_transactions_task

    assert callable(sync_teller_transactions_task.delay)


def test_mx_webhook_imports_sync_task():
    """The MX sync task module can be imported (no circular imports)."""
    from app.workers.tasks.sync_tasks import sync_mx_transactions_task

    assert callable(sync_mx_transactions_task.delay)


# ---------------------------------------------------------------------------
# Org-id verification (defense-in-depth)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.core.cache.delete_pattern", new_callable=AsyncMock)
async def test_invalidate_org_caches_clears_all_patterns(mock_del):
    """Cache invalidation helper clears transactions, trends, and dashboard."""
    from app.workers.tasks.sync_tasks import _invalidate_org_caches

    await _invalidate_org_caches("org-abc")

    assert mock_del.call_count == 3
    patterns = [c.args[0] for c in mock_del.call_args_list]
    assert "transactions:org-abc:*" in patterns
    assert "ie:*:org-abc:*" in patterns
    assert "dashboard:summary:org-abc:*" in patterns


def test_sync_tasks_have_org_verification_in_source():
    """All three sync tasks contain org mismatch checks in source code."""
    import inspect
    from app.workers.tasks.sync_tasks import (
        _sync_plaid_transactions_async,
        _sync_teller_transactions_async,
        _sync_mx_transactions_async,
    )

    for fn in [_sync_plaid_transactions_async, _sync_teller_transactions_async, _sync_mx_transactions_async]:
        source = inspect.getsource(fn)
        assert "org mismatch" in source, f"{fn.__name__} missing org verification"
