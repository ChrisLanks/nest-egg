"""Tests for the Milestone service (net worth milestones and all-time highs)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.notification import Notification, NotificationPriority, NotificationType
from app.services.milestone_service import (
    MILESTONE_THRESHOLDS,
    _format_milestone,
    _notification_exists_today,
    check_milestones,
    get_milestone_summary,
)
from app.utils.datetime_utils import utc_now

# ---------------------------------------------------------------------------
# Format helper
# ---------------------------------------------------------------------------


class TestFormatMilestone:
    """Test the milestone label formatter."""

    def test_millions(self):
        assert _format_milestone(1_000_000) == "$1M"
        assert _format_milestone(5_000_000) == "$5M"

    def test_thousands(self):
        assert _format_milestone(10_000) == "$10,000"
        assert _format_milestone(250_000) == "$250,000"
        assert _format_milestone(500_000) == "$500,000"

    def test_non_round_value(self):
        assert _format_milestone(12_345) == "$12,345"


# ---------------------------------------------------------------------------
# check_milestones
# ---------------------------------------------------------------------------


class TestCheckMilestones:
    """Test milestone detection logic."""

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_no_previous_snapshot_no_milestones(self, mock_notify, db, test_user):
        """With no previous data and net worth below first threshold, no milestones."""
        result = await check_milestones(db, test_user.organization_id, Decimal("5000"))
        assert result == []

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_crossing_first_milestone(self, mock_notify, db, test_user):
        """Crossing from 0 to above $10k should trigger the $10k milestone."""
        # Add a previous snapshot below the threshold
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("8000"),
            total_assets=Decimal("8000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("12000"))

        milestone_types = [m["type"] for m in result]
        assert "milestone" in milestone_types
        thresholds_hit = [m["threshold"] for m in result if m["type"] == "milestone"]
        assert 10_000 in thresholds_hit
        mock_notify.assert_called()

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_crossing_multiple_milestones(self, mock_notify, db, test_user):
        """Jumping from $9k to $60k should trigger $10k, $25k, $50k."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("9000"),
            total_assets=Decimal("9000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("60000"))

        thresholds_hit = [m["threshold"] for m in result if m["type"] == "milestone"]
        assert 10_000 in thresholds_hit
        assert 25_000 in thresholds_hit
        assert 50_000 in thresholds_hit
        assert 100_000 not in thresholds_hit

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_multiple_milestones_creates_single_notification(
        self, mock_notify, db, test_user
    ):
        """Crossing multiple thresholds should only create ONE notification for the highest."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("9000"),
            total_assets=Decimal("9000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        await check_milestones(db, test_user.organization_id, Decimal("60000"))

        # Only one notification created despite crossing $10k, $25k, $50k
        milestone_calls = [
            c
            for c in mock_notify.call_args_list
            if c.kwargs.get("title", "").startswith("Milestone")
        ]
        assert len(milestone_calls) == 1
        assert "$50,000" in milestone_calls[0].kwargs["title"]

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_massive_jump_only_notifies_highest(self, mock_notify, db, test_user):
        """Jumping from $5k to $2M should only notify for $1M (the highest crossed)."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("5000"),
            total_assets=Decimal("5000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("2000000"))

        # Return value still lists all crossed thresholds
        thresholds_hit = [m["threshold"] for m in result if m["type"] == "milestone"]
        assert 10_000 in thresholds_hit
        assert 1_000_000 in thresholds_hit

        # But only ONE milestone notification — for $1M
        milestone_calls = [
            c
            for c in mock_notify.call_args_list
            if c.kwargs.get("title", "").startswith("Milestone")
        ]
        assert len(milestone_calls) == 1
        assert "$1M" in milestone_calls[0].kwargs["title"]

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_single_milestone_crossing_creates_one_notification(
        self, mock_notify, db, test_user
    ):
        """Crossing exactly one threshold still creates one notification."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("8000"),
            total_assets=Decimal("8000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        await check_milestones(db, test_user.organization_id, Decimal("12000"))

        milestone_calls = [
            c
            for c in mock_notify.call_args_list
            if c.kwargs.get("title", "").startswith("Milestone")
        ]
        assert len(milestone_calls) == 1
        assert "$10,000" in milestone_calls[0].kwargs["title"]

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_no_milestone_when_already_above(self, mock_notify, db, test_user):
        """No milestone if previous was already above the threshold."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("30000"),
            total_assets=Decimal("30000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("35000"))
        thresholds_hit = [m["threshold"] for m in result if m["type"] == "milestone"]
        assert 10_000 not in thresholds_hit
        assert 25_000 not in thresholds_hit

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_all_time_high_detected(self, mock_notify, db, test_user):
        """All-time high should be detected when current exceeds all past values."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("50000"),
            total_assets=Decimal("50000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("55000"))
        ath_entries = [m for m in result if m["type"] == "all_time_high"]
        assert len(ath_entries) == 1
        assert ath_entries[0]["net_worth"] == 55000.0
        assert ath_entries[0]["previous_ath"] == 50000.0

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_no_ath_when_below_previous(self, mock_notify, db, test_user):
        """All-time high should NOT fire when current is below previous ATH."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("100000"),
            total_assets=Decimal("100000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("95000"))
        ath_entries = [m for m in result if m["type"] == "all_time_high"]
        assert len(ath_entries) == 0

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_no_ath_when_no_previous_snapshots(self, mock_notify, db, test_user):
        """No ATH if there are no previous snapshots (previous_ath_value is None)."""
        result = await check_milestones(db, test_user.organization_id, Decimal("50000"))
        ath_entries = [m for m in result if m["type"] == "all_time_high"]
        assert len(ath_entries) == 0


# ---------------------------------------------------------------------------
# get_milestone_summary
# ---------------------------------------------------------------------------


class TestGetMilestoneSummary:
    """Test milestone summary generation."""

    @pytest.mark.asyncio
    async def test_no_snapshots(self, db, test_user):
        """With no snapshots, summary should have empty milestones and zero ATH."""
        summary = await get_milestone_summary(db, test_user.organization_id)

        assert summary["milestones_achieved"] == []
        assert summary["all_time_high"]["value"] == 0.0
        assert summary["next_milestone"] == MILESTONE_THRESHOLDS[0]

    @pytest.mark.asyncio
    async def test_summary_with_milestones_achieved(self, db, test_user):
        """Summary should list all achieved milestones based on current net worth."""
        snap = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today(),
            total_net_worth=Decimal("75000"),
            total_assets=Decimal("80000"),
            total_liabilities=Decimal("5000"),
        )
        db.add(snap)
        await db.commit()

        summary = await get_milestone_summary(db, test_user.organization_id)

        achieved_thresholds = [m["threshold"] for m in summary["milestones_achieved"]]
        assert 10_000 in achieved_thresholds
        assert 25_000 in achieved_thresholds
        assert 50_000 in achieved_thresholds
        assert 100_000 not in achieved_thresholds
        assert summary["next_milestone"] == 100_000

    @pytest.mark.asyncio
    async def test_summary_all_time_high(self, db, test_user):
        """Summary should report the all-time high value and date."""
        snap1 = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=30),
            total_net_worth=Decimal("40000"),
            total_assets=Decimal("40000"),
            total_liabilities=Decimal("0"),
        )
        snap2 = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today(),
            total_net_worth=Decimal("60000"),
            total_assets=Decimal("60000"),
            total_liabilities=Decimal("0"),
        )
        db.add_all([snap1, snap2])
        await db.commit()

        summary = await get_milestone_summary(db, test_user.organization_id)

        assert summary["all_time_high"]["value"] == 60000.0
        assert summary["all_time_high"]["is_current"] is True

    @pytest.mark.asyncio
    async def test_summary_ath_not_current(self, db, test_user):
        """ATH should not be flagged as current when latest snapshot is lower."""
        snap_old = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=30),
            total_net_worth=Decimal("100000"),
            total_assets=Decimal("100000"),
            total_liabilities=Decimal("0"),
        )
        snap_latest = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today(),
            total_net_worth=Decimal("80000"),
            total_assets=Decimal("80000"),
            total_liabilities=Decimal("0"),
        )
        db.add_all([snap_old, snap_latest])
        await db.commit()

        summary = await get_milestone_summary(db, test_user.organization_id)

        assert summary["all_time_high"]["value"] == 100000.0
        assert summary["all_time_high"]["is_current"] is False

    @pytest.mark.asyncio
    async def test_next_milestone_when_all_achieved(self, db, test_user):
        """Next milestone should be None when all thresholds exceeded."""
        snap = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today(),
            total_net_worth=Decimal("20000000"),
            total_assets=Decimal("20000000"),
            total_liabilities=Decimal("0"),
        )
        db.add(snap)
        await db.commit()

        summary = await get_milestone_summary(db, test_user.organization_id)

        assert summary["next_milestone"] is None
        assert len(summary["milestones_achieved"]) == len(MILESTONE_THRESHOLDS)


# ---------------------------------------------------------------------------
# Deduplication — concurrent syncs must not create duplicate notifications
# ---------------------------------------------------------------------------


class TestMilestoneDeduplication:
    """Verify that calling check_milestones twice in the same day (simulating
    two concurrent account syncs) only produces one notification per event."""

    @pytest.mark.asyncio
    async def test_milestone_not_duplicated_on_second_call(self, db, test_user):
        """Second check_milestones call on the same day skips the notification
        because one already exists with the same type + title."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("8000"),
            total_assets=Decimal("8000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        # First call — should create the notification
        await check_milestones(db, test_user.organization_id, Decimal("12000"))

        result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.type == NotificationType.MILESTONE,
            )
        )
        after_first = result.scalars().all()
        assert len(after_first) == 1

        # Second call (same day, same net worth) — must NOT add another row
        await check_milestones(db, test_user.organization_id, Decimal("12000"))

        result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.type == NotificationType.MILESTONE,
            )
        )
        after_second = result.scalars().all()
        assert len(after_second) == 1

    @pytest.mark.asyncio
    async def test_ath_not_duplicated_on_second_call(self, db, test_user):
        """Second check_milestones call on the same day skips the ATH notification."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("50000"),
            total_assets=Decimal("50000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        await check_milestones(db, test_user.organization_id, Decimal("55000"))

        result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.type == NotificationType.ALL_TIME_HIGH,
            )
        )
        assert len(result.scalars().all()) == 1

        await check_milestones(db, test_user.organization_id, Decimal("55000"))

        result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.type == NotificationType.ALL_TIME_HIGH,
            )
        )
        assert len(result.scalars().all()) == 1

    @pytest.mark.asyncio
    async def test_notification_exists_today_helper(self, db, test_user):
        """_notification_exists_today returns False before creation, True after."""
        assert not await _notification_exists_today(
            db,
            test_user.organization_id,
            NotificationType.MILESTONE,
            "Milestone reached: $10,000!",
        )

        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("8000"),
            total_assets=Decimal("8000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        await check_milestones(db, test_user.organization_id, Decimal("12000"))

        assert await _notification_exists_today(
            db,
            test_user.organization_id,
            NotificationType.MILESTONE,
            "Milestone reached: $10,000!",
        )


# ---------------------------------------------------------------------------
# _notification_exists_today — isolation and time-window edge cases
# ---------------------------------------------------------------------------


class TestNotificationExistsToday:
    """Unit tests for the dedup helper in isolation."""

    @pytest.mark.asyncio
    async def test_different_org_not_matched(self, db, test_user, second_organization):
        """A notification for a different org must not block the current org."""
        notif = Notification(
            id=uuid4(),
            organization_id=second_organization.id,
            type=NotificationType.MILESTONE,
            title="Milestone reached: $10,000!",
            message="msg",
            priority=NotificationPriority.LOW,
        )
        db.add(notif)
        await db.commit()

        # Current org has no notification — should return False
        assert not await _notification_exists_today(
            db,
            test_user.organization_id,
            NotificationType.MILESTONE,
            "Milestone reached: $10,000!",
        )

    @pytest.mark.asyncio
    async def test_different_type_not_matched(self, db, test_user):
        """A notification with a different type must not trigger the dedup."""
        notif = Notification(
            id=uuid4(),
            organization_id=test_user.organization_id,
            type=NotificationType.ALL_TIME_HIGH,
            title="Milestone reached: $10,000!",
            message="msg",
            priority=NotificationPriority.LOW,
        )
        db.add(notif)
        await db.commit()

        assert not await _notification_exists_today(
            db,
            test_user.organization_id,
            NotificationType.MILESTONE,
            "Milestone reached: $10,000!",
        )

    @pytest.mark.asyncio
    async def test_yesterday_notification_does_not_block_today(self, db, test_user):
        """A notification created yesterday must not suppress today's."""
        yesterday_start = datetime(*date.today().timetuple()[:3], tzinfo=timezone.utc) - timedelta(
            days=1
        )
        notif = Notification(
            id=uuid4(),
            organization_id=test_user.organization_id,
            type=NotificationType.MILESTONE,
            title="Milestone reached: $10,000!",
            message="msg",
            priority=NotificationPriority.LOW,
        )
        # Back-date the created_at to yesterday
        notif.created_at = yesterday_start
        db.add(notif)
        await db.commit()

        assert not await _notification_exists_today(
            db,
            test_user.organization_id,
            NotificationType.MILESTONE,
            "Milestone reached: $10,000!",
        )


# ---------------------------------------------------------------------------
# check_milestones — boundary and edge cases
# ---------------------------------------------------------------------------


class TestCheckMilestoneBoundaries:
    """Edge cases for threshold crossing logic."""

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_previous_exactly_at_threshold_no_crossing(self, mock_notify, db, test_user):
        """previous == threshold means it was already crossed; no new milestone."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("10000"),
            total_assets=Decimal("10000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("10500"))
        thresholds_hit = [m["threshold"] for m in result if m["type"] == "milestone"]
        assert 10_000 not in thresholds_hit
        milestone_calls = [
            c
            for c in mock_notify.call_args_list
            if c.kwargs.get("title", "").startswith("Milestone")
        ]
        assert len(milestone_calls) == 0

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_current_exactly_at_threshold_triggers(self, mock_notify, db, test_user):
        """previous < threshold == current should trigger the milestone."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("9999"),
            total_assets=Decimal("9999"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("10000"))
        thresholds_hit = [m["threshold"] for m in result if m["type"] == "milestone"]
        assert 10_000 in thresholds_hit

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_negative_net_worth_no_milestones(self, mock_notify, db, test_user):
        """Negative net worth should never trigger any milestone."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("-5000"),
            total_assets=Decimal("0"),
            total_liabilities=Decimal("5000"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("-1000"))
        assert result == []
        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_milestone_and_ath_both_fire_same_call(self, mock_notify, db, test_user):
        """Crossing a milestone threshold AND setting an ATH should both fire."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("8000"),
            total_assets=Decimal("8000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("12000"))

        types = {m["type"] for m in result}
        assert "milestone" in types
        assert "all_time_high" in types

        titles = {call.kwargs["title"] for call in mock_notify.call_args_list}
        assert any("Milestone" in t for t in titles)
        assert any("all-time high" in t.lower() for t in titles)

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_user_scoped_snapshots_excluded_from_previous(self, mock_notify, db, test_user):
        """Per-user snapshots must not be used as the previous household value.

        A user-scoped snapshot at $30k should not prevent the $10k milestone from
        firing — only household snapshots (user_id IS NULL) count as previous.
        """
        # User-scoped snapshot at $30k — above $10k, $25k
        user_snap = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("30000"),
            total_assets=Decimal("30000"),
            total_liabilities=Decimal("0"),
        )
        db.add(user_snap)
        await db.commit()

        # No household snapshot → previous defaults to 0, so $10k threshold fires
        result = await check_milestones(db, test_user.organization_id, Decimal("12000"))
        thresholds_hit = [m["threshold"] for m in result if m["type"] == "milestone"]
        # $10k fires (previous=0, current=12k); $25k and $30k don't (12k < 25k)
        assert 10_000 in thresholds_hit
        assert 25_000 not in thresholds_hit

    @pytest.mark.asyncio
    @patch(
        "app.services.milestone_service.NotificationService.create_notification",
        new_callable=AsyncMock,
    )
    async def test_milestone_result_contains_expected_fields(self, mock_notify, db, test_user):
        """Each milestone dict in the return value must carry the expected keys."""
        prev = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today() - timedelta(days=1),
            total_net_worth=Decimal("8000"),
            total_assets=Decimal("8000"),
            total_liabilities=Decimal("0"),
        )
        db.add(prev)
        await db.commit()

        result = await check_milestones(db, test_user.organization_id, Decimal("12000"))
        m = next(r for r in result if r["type"] == "milestone")
        assert m["threshold"] == 10_000
        assert m["label"] == "$10,000"
        assert m["net_worth"] == 12_000.0
        assert m["date"] == utc_now().date().isoformat()


# ---------------------------------------------------------------------------
# get_milestone_summary — additional coverage
# ---------------------------------------------------------------------------


class TestGetMilestoneSummaryExtended:
    """Additional edge cases for get_milestone_summary."""

    @pytest.mark.asyncio
    async def test_summary_ath_date_is_set(self, db, test_user):
        """all_time_high.date must be the ISO date string of the ATH snapshot."""
        snap_date = date.today() - timedelta(days=5)
        snap = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=snap_date,
            total_net_worth=Decimal("30000"),
            total_assets=Decimal("30000"),
            total_liabilities=Decimal("0"),
        )
        db.add(snap)
        await db.commit()

        summary = await get_milestone_summary(db, test_user.organization_id)
        assert summary["all_time_high"]["date"] == snap_date.isoformat()

    @pytest.mark.asyncio
    async def test_summary_user_scoped_snapshots_excluded(self, db, test_user):
        """Per-user snapshots must not affect the summary's current net worth."""
        user_snap = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            snapshot_date=date.today(),
            total_net_worth=Decimal("200000"),
            total_assets=Decimal("200000"),
            total_liabilities=Decimal("0"),
        )
        db.add(user_snap)
        await db.commit()

        summary = await get_milestone_summary(db, test_user.organization_id)
        # No household snapshot → milestones_achieved should be empty
        assert summary["milestones_achieved"] == []

    @pytest.mark.asyncio
    async def test_summary_milestone_labels_formatted(self, db, test_user):
        """Achieved milestone entries must include correctly formatted labels."""
        snap = NetWorthSnapshot(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=None,
            snapshot_date=date.today(),
            total_net_worth=Decimal("1500000"),
            total_assets=Decimal("1500000"),
            total_liabilities=Decimal("0"),
        )
        db.add(snap)
        await db.commit()

        summary = await get_milestone_summary(db, test_user.organization_id)
        labels = {m["label"] for m in summary["milestones_achieved"]}
        assert "$1M" in labels
        assert "$10,000" in labels
        assert "$500,000" in labels
