"""Tests for the Celery snapshot tasks (portfolio net-worth capture)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from app.workers.tasks.snapshot_tasks import _calculate_offset_seconds


@pytest.mark.unit
class TestCalculateOffsetSeconds:
    """Tests for the deterministic org-offset function."""

    def test_returns_int_in_valid_range(self):
        """Offset should be 0–86399 seconds (within a 24-hour window)."""
        org_id = uuid4()
        offset = _calculate_offset_seconds(org_id)
        assert isinstance(offset, int)
        assert 0 <= offset <= 86399

    def test_same_org_always_same_offset(self):
        """Same organisation ID must always produce the same offset (deterministic)."""
        org_id = uuid4()
        assert _calculate_offset_seconds(org_id) == _calculate_offset_seconds(org_id)

    def test_different_orgs_likely_different_offsets(self):
        """Different org IDs should (almost always) produce different offsets."""
        offsets = {_calculate_offset_seconds(uuid4()) for _ in range(20)}
        # With 20 random orgs spread across 86400 seconds the probability of
        # all colliding is astronomically small
        assert len(offsets) > 1

    def test_offset_is_multiple_of_60(self):
        """Offsets are quantised to minute boundaries (60-second granularity)."""
        for _ in range(10):
            offset = _calculate_offset_seconds(uuid4())
            assert offset % 60 == 0

    def test_accepts_string_org_id(self):
        """Should work when org_id is already a string (as stored by Celery)."""
        org_id_str = str(uuid4())
        offset = _calculate_offset_seconds(org_id_str)
        assert 0 <= offset <= 86399

    def test_string_and_uuid_same_result(self):
        """str(org_id) and UUID obj should produce identical offsets."""
        org_id = uuid4()
        assert _calculate_offset_seconds(str(org_id)) == _calculate_offset_seconds(org_id)


@pytest.mark.unit
class TestOrchestratePortfolioSnapshots:
    """Tests for the dispatch logic inside the Beat entry-point task."""

    def test_dispatches_one_task_per_org(self):
        """Should call apply_async once for every org in the list."""
        from app.workers.tasks.snapshot_tasks import _dispatch_snapshot_tasks

        org1 = MagicMock()
        org1.id = uuid4()
        org2 = MagicMock()
        org2.id = uuid4()

        with patch(
            "app.workers.tasks.snapshot_tasks.capture_org_portfolio_snapshot"
        ) as mock_task:
            mock_task.apply_async = MagicMock()
            _dispatch_snapshot_tasks([org1, org2])
            assert mock_task.apply_async.call_count == 2

    def test_countdown_is_nonnegative(self):
        """The countdown passed to apply_async should never be negative."""
        from app.workers.tasks.snapshot_tasks import _dispatch_snapshot_tasks

        org = MagicMock()
        org.id = uuid4()

        with patch(
            "app.workers.tasks.snapshot_tasks.capture_org_portfolio_snapshot"
        ) as mock_task:
            mock_task.apply_async = MagicMock()
            _dispatch_snapshot_tasks([org])
            _, kwargs = mock_task.apply_async.call_args
            assert kwargs["countdown"] >= 0

    def test_empty_org_list_dispatches_nothing(self):
        """With no organisations, no tasks should be enqueued."""
        from app.workers.tasks.snapshot_tasks import _dispatch_snapshot_tasks

        with patch(
            "app.workers.tasks.snapshot_tasks.capture_org_portfolio_snapshot"
        ) as mock_task:
            mock_task.apply_async = MagicMock()
            _dispatch_snapshot_tasks([])
            mock_task.apply_async.assert_not_called()
