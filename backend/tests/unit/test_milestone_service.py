"""Tests for the Milestone service (net worth milestones and all-time highs)."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.net_worth_snapshot import NetWorthSnapshot
from app.services.milestone_service import (
    MILESTONE_THRESHOLDS,
    _format_milestone,
    check_milestones,
    get_milestone_summary,
)

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
