"""Unit tests for SnapshotScheduler — offset calculation, scheduling logic."""

from datetime import date, datetime
from uuid import uuid4

import pytest

from app.services.snapshot_scheduler import SnapshotScheduler


@pytest.fixture
def scheduler():
    return SnapshotScheduler()


class TestCalculateOffsetHours:
    def test_deterministic(self, scheduler):
        """Same org ID always produces same offset."""
        org_id = uuid4()
        assert scheduler.calculate_offset_hours(org_id) == scheduler.calculate_offset_hours(org_id)

    def test_different_orgs_different_offsets(self, scheduler):
        """Different org IDs should (almost certainly) produce different offsets."""
        offsets = {scheduler.calculate_offset_hours(uuid4()) for _ in range(20)}
        assert len(offsets) > 1

    def test_range_0_to_24(self, scheduler):
        """Offset must be in [0, 24) range."""
        for _ in range(50):
            offset = scheduler.calculate_offset_hours(uuid4())
            assert 0 <= offset < 24


class TestGetNextRunTime:
    def test_future_today_returns_today(self, scheduler):
        """If scheduled time hasn't passed yet, return today's time."""
        org_id = uuid4()
        # Use midnight as 'now' — offset is always > 0, so scheduled time is in the future
        now = datetime(2025, 6, 15, 0, 0, 0)
        offset = scheduler.calculate_offset_hours(org_id)

        if offset > 0:
            next_run = scheduler.get_next_run_time(org_id, now)
            assert next_run.date() == date(2025, 6, 15)

    def test_past_today_returns_tomorrow(self, scheduler):
        """If scheduled time has passed, return tomorrow's time."""
        org_id = uuid4()
        # Use 23:59 as 'now' — scheduled time is almost certainly in the past
        now = datetime(2025, 6, 15, 23, 59, 59)
        next_run = scheduler.get_next_run_time(org_id, now)
        assert next_run.date() == date(2025, 6, 16)

    def test_consistent_with_offset(self, scheduler):
        """Next run time should be midnight + offset hours."""
        from datetime import timedelta

        org_id = uuid4()
        now = datetime(2025, 6, 15, 0, 0, 0)
        offset = scheduler.calculate_offset_hours(org_id)
        next_run = scheduler.get_next_run_time(org_id, now)

        # Compute expected time the same way the scheduler does (timedelta)
        expected = datetime(2025, 6, 15, 0, 0, 0) + timedelta(hours=offset)
        assert next_run.hour == expected.hour
        assert next_run.minute == expected.minute

    def test_default_now_used_when_none(self, scheduler):
        """Should use current time when now=None."""
        org_id = uuid4()
        next_run = scheduler.get_next_run_time(org_id, now=None)
        assert next_run is not None
        # Should be today or tomorrow
        from datetime import timedelta

        today = datetime.now().date()
        assert next_run.date() in (today, today + timedelta(days=1))


class TestShouldCaptureSnapshot:
    """Tests for should_capture_snapshot."""

    @pytest.mark.asyncio
    async def test_snapshot_exists_returns_false(self, scheduler):
        """Should return False when snapshot already exists for today."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # exists
        db.execute = AsyncMock(return_value=mock_result)

        org_id = uuid4()
        now = datetime(2025, 6, 15, 12, 0, 0)
        result = await scheduler.should_capture_snapshot(db, org_id, now)
        assert result is False

    @pytest.mark.asyncio
    async def test_next_run_tomorrow_returns_false(self, scheduler):
        """When get_next_run_time returns tomorrow, next_run.date() > today, returns False."""
        from unittest.mock import AsyncMock, MagicMock, patch

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # no existing snapshot
        db.execute = AsyncMock(return_value=mock_result)

        org_id = uuid4()
        now = datetime(2025, 6, 15, 12, 0, 0)

        # Mock get_next_run_time to return tomorrow
        with patch.object(
            scheduler,
            "get_next_run_time",
            return_value=datetime(2025, 6, 16, 5, 0, 0),
        ):
            result = await scheduler.should_capture_snapshot(db, org_id, now)
        assert result is False

    @pytest.mark.asyncio
    async def test_next_run_today_returns_true(self, scheduler):
        """When get_next_run_time returns today, returns True (no snapshot exists)."""
        from unittest.mock import AsyncMock, MagicMock, patch

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        org_id = uuid4()
        now = datetime(2025, 6, 15, 12, 0, 0)

        # Mock get_next_run_time to return later today
        with patch.object(
            scheduler,
            "get_next_run_time",
            return_value=datetime(2025, 6, 15, 18, 0, 0),
        ):
            result = await scheduler.should_capture_snapshot(db, org_id, now)
        assert result is True


class TestCaptureOrganizationSnapshot:
    """Tests for capture_organization_snapshot."""

    @pytest.mark.asyncio
    async def test_no_user_returns_false(self, scheduler):
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        result = await scheduler.capture_organization_snapshot(db, uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_exception_returns_false(self, scheduler):
        from unittest.mock import AsyncMock

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=RuntimeError("DB error"))

        result = await scheduler.capture_organization_snapshot(db, uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_successful_capture(self, scheduler):
        from unittest.mock import AsyncMock, MagicMock, patch

        db = AsyncMock()
        mock_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db.execute = AsyncMock(return_value=mock_result)

        mock_portfolio = MagicMock()
        mock_portfolio.total_value = 100000

        with (
            patch(
                "app.services.snapshot_scheduler.snapshot_service.capture_snapshot",
                new=AsyncMock(),
            ),
            patch(
                "app.api.v1.holdings.get_portfolio_summary",
                new=AsyncMock(return_value=mock_portfolio),
            ),
        ):
            result = await scheduler.capture_organization_snapshot(db, uuid4())
        assert result is True


class TestAcquireLock:
    """Tests for _acquire_lock."""

    @pytest.mark.asyncio
    async def test_redis_unavailable_returns_true(self, scheduler):
        """Should return True (run anyway) when Redis is unavailable."""
        from unittest.mock import patch

        with patch("app.services.snapshot_scheduler.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://nonexistent:6379"
            result = await scheduler._acquire_lock()
        assert result is True

    @pytest.mark.asyncio
    async def test_lock_acquired(self, scheduler):
        """Should return True when lock acquired successfully."""
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)
        mock_client.aclose = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_client):
            result = await scheduler._acquire_lock()
        assert result is True

    @pytest.mark.asyncio
    async def test_lock_not_acquired(self, scheduler):
        """Should return False when lock already held."""
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=None)
        mock_client.aclose = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_client):
            result = await scheduler._acquire_lock()
        assert result is False


class TestCheckAndCaptureAll:
    """Tests for check_and_capture_all."""

    @pytest.mark.asyncio
    async def test_skips_when_lock_not_acquired(self, scheduler):
        from unittest.mock import AsyncMock, patch

        with patch.object(scheduler, "_acquire_lock", new=AsyncMock(return_value=False)):
            await scheduler.check_and_capture_all()
            # Should return early, no further calls

    @pytest.mark.asyncio
    async def test_captures_snapshots_for_orgs(self, scheduler):
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_org = MagicMock()
        mock_org.id = uuid4()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_org]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_capture = AsyncMock(return_value=True)

        with (
            patch.object(scheduler, "_acquire_lock", new=AsyncMock(return_value=True)),
            patch("app.services.snapshot_scheduler.AsyncSessionLocal", return_value=mock_session),
            patch.object(scheduler, "should_capture_snapshot", new=AsyncMock(return_value=True)),
            patch.object(scheduler, "capture_organization_snapshot", mock_capture),
            patch("asyncio.sleep", new=AsyncMock()),
        ):
            await scheduler.check_and_capture_all()

        mock_capture.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_exception(self, scheduler):
        from unittest.mock import AsyncMock, patch

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=RuntimeError("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.object(scheduler, "_acquire_lock", new=AsyncMock(return_value=True)),
            patch("app.services.snapshot_scheduler.AsyncSessionLocal", return_value=mock_session),
        ):
            # Should not raise
            await scheduler.check_and_capture_all()


class TestCleanupExpiredTokens:
    """Tests for cleanup_expired_tokens."""

    @pytest.mark.asyncio
    async def test_deletes_expired_tokens(self, scheduler):
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_session = AsyncMock()
        mock_r1 = MagicMock()
        mock_r1.rowcount = 3
        mock_r2 = MagicMock()
        mock_r2.rowcount = 1
        mock_session.execute = AsyncMock(side_effect=[mock_r1, mock_r2])
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.snapshot_scheduler.AsyncSessionLocal", return_value=mock_session):
            await scheduler.cleanup_expired_tokens()

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_exception(self, scheduler):
        from unittest.mock import AsyncMock, patch

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=RuntimeError("DB error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.snapshot_scheduler.AsyncSessionLocal", return_value=mock_session):
            # Should not raise
            await scheduler.cleanup_expired_tokens()


class TestStartStop:
    """Tests for start and stop no-op methods."""

    @pytest.mark.asyncio
    async def test_start_is_noop(self, scheduler):
        await scheduler.start()

    @pytest.mark.asyncio
    async def test_stop_is_noop(self, scheduler):
        await scheduler.stop()
