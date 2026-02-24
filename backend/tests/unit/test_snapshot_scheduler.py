"""Unit tests for SnapshotScheduler — offset calculation, scheduling logic."""

import pytest
from datetime import datetime, date
from uuid import uuid4, UUID

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
