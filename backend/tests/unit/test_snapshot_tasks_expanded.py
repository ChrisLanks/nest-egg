"""Expanded tests for snapshot_tasks — covers capture_org_portfolio_snapshot and cleanup."""

import sys
from unittest.mock import MagicMock

_celery_stub = MagicMock()
sys.modules.setdefault("celery", _celery_stub)
sys.modules.setdefault("app.workers.celery_app", _celery_stub)

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.workers.tasks.snapshot_tasks import (
    _dispatch_snapshot_tasks,
    _fetch_all_organizations,
    capture_org_portfolio_snapshot,
    cleanup_expired_auth_tokens,
)


@pytest.mark.unit
class TestFetchAllOrganizations:
    """Test synchronous org fetch wrapper."""

    def test_returns_orgs_via_asyncio_run(self):
        org1 = Mock()
        org1.id = uuid4()

        async def mock_inner():
            return [org1]

        with (
            patch("app.workers.utils.get_celery_session"),
            patch("asyncio.run") as mock_run,
        ):
            mock_run.return_value = [org1]
            result = _fetch_all_organizations()

        assert len(result) == 1


@pytest.mark.unit
class TestCaptureOrgPortfolioSnapshot:
    """Test per-org snapshot capture."""

    def test_task_calls_asyncio_run(self):
        """The celery task wraps async logic in asyncio.run."""
        with patch("asyncio.run") as mock_run:
            capture_org_portfolio_snapshot(str(uuid4()))
            mock_run.assert_called_once()


@pytest.mark.unit
class TestCleanupExpiredAuthTokens:
    """Test token cleanup task."""

    def test_task_calls_asyncio_run(self):
        with patch("asyncio.run") as mock_run:
            cleanup_expired_auth_tokens()
            mock_run.assert_called_once()


@pytest.mark.unit
class TestDispatchSnapshotTasksReturnValue:
    """Test return value of _dispatch_snapshot_tasks."""

    def test_returns_count(self):
        org_ids = [uuid4() for _ in range(3)]

        with patch("app.workers.tasks.snapshot_tasks.capture_org_portfolio_snapshot") as mock_task:
            mock_task.apply_async = MagicMock()
            result = _dispatch_snapshot_tasks(org_ids)

        assert result == 3

    def test_empty_returns_zero(self):
        with patch("app.workers.tasks.snapshot_tasks.capture_org_portfolio_snapshot") as mock_task:
            mock_task.apply_async = MagicMock()
            result = _dispatch_snapshot_tasks([])

        assert result == 0

    def test_org_ids_passed_as_strings(self):
        org_id = uuid4()

        with patch("app.workers.tasks.snapshot_tasks.capture_org_portfolio_snapshot") as mock_task:
            mock_task.apply_async = MagicMock()
            _dispatch_snapshot_tasks([org_id])

        args_passed = mock_task.apply_async.call_args[1]["args"]
        assert isinstance(args_passed[0], str)
