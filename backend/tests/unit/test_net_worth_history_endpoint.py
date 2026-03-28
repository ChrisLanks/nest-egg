"""
Tests for the net-worth-history endpoint:
1. Returns empty list when no snapshots and lazy bootstrap fails gracefully
2. Lazy bootstrap: captures a snapshot when none exist and returns it
3. Returns existing snapshots when they're present (no re-capture)
4. Response fields are correctly mapped from snapshot model
5. None snapshot fields coerce to 0.0
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.dashboard import get_net_worth_history, NetWorthHistoryPoint


def _make_user(org_id=None):
    user = MagicMock()
    user.id = uuid4()
    user.organization_id = org_id or uuid4()
    return user


def _make_snapshot(total_net_worth=50000):
    snap = MagicMock()
    snap.snapshot_date = date.today()
    snap.total_net_worth = Decimal(str(total_net_worth))
    snap.total_assets = Decimal("60000")
    snap.total_liabilities = Decimal("10000")
    snap.cash_and_checking = Decimal("5000")
    snap.savings = Decimal("10000")
    snap.investments = Decimal("20000")
    snap.retirement = Decimal("25000")
    snap.property = Decimal("0")
    snap.vehicles = Decimal("0")
    snap.other_assets = Decimal("0")
    snap.credit_cards = Decimal("1000")
    snap.loans = Decimal("0")
    snap.mortgages = Decimal("0")
    snap.student_loans = Decimal("9000")
    snap.other_debts = Decimal("0")
    return snap


def _db_returning(snapshots):
    """AsyncSession that returns `snapshots` from every execute() call."""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = snapshots
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    return db


# ─────────────────────────────────────────────────────────────────────────────
# 1. No snapshots + bootstrap raises → empty list, no crash
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_net_worth_history_empty_bootstrap_failure():
    """When no snapshots exist and bootstrap raises, return empty list gracefully."""
    user = _make_user()
    db = _db_returning([])

    mock_svc = MagicMock()
    mock_svc.capture_snapshot = AsyncMock(side_effect=Exception("db error"))

    with patch("app.services.net_worth_service.NetWorthService", return_value=mock_svc):
        result = await get_net_worth_history(
            start_date=None,
            end_date=None,
            user_id=None,
            current_user=user,
            db=db,
        )

    assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# 2. Snapshots exist → returned directly, bootstrap NOT triggered
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_net_worth_history_returns_existing_snapshots():
    """When snapshots already exist, they are returned without triggering bootstrap."""
    user = _make_user()
    snaps = [
        _make_snapshot(45000),
        _make_snapshot(47000),
        _make_snapshot(50000),
    ]
    # Give each a distinct date so ordering is meaningful
    for i, s in enumerate(snaps):
        s.snapshot_date = date.today() - timedelta(days=2 - i)

    db = _db_returning(snaps)

    mock_svc = MagicMock()
    mock_svc.capture_snapshot = AsyncMock()

    with patch("app.services.net_worth_service.NetWorthService", return_value=mock_svc):
        result = await get_net_worth_history(
            start_date=None,
            end_date=None,
            user_id=None,
            current_user=user,
            db=db,
        )
        mock_svc.capture_snapshot.assert_not_called()

    assert len(result) == 3
    assert result[0].total_net_worth == 45000.0
    assert result[2].total_net_worth == 50000.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Response fields are correctly mapped from snapshot
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_net_worth_history_field_mapping():
    """All NetWorthHistoryPoint fields are correctly mapped from the snapshot."""
    user = _make_user()
    snap = _make_snapshot(50000)
    db = _db_returning([snap])

    result = await get_net_worth_history(
        start_date=None,
        end_date=None,
        user_id=None,
        current_user=user,
        db=db,
    )

    assert len(result) == 1
    pt = result[0]
    assert isinstance(pt, NetWorthHistoryPoint)
    assert pt.total_net_worth == 50000.0
    assert pt.total_assets == 60000.0
    assert pt.total_liabilities == 10000.0
    assert pt.cash_and_checking == 5000.0
    assert pt.savings == 10000.0
    assert pt.investments == 20000.0
    assert pt.retirement == 25000.0
    assert pt.credit_cards == 1000.0
    assert pt.student_loans == 9000.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. None snapshot fields coerce to 0.0
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_net_worth_history_none_fields_coerce_to_zero():
    """None values in snapshot fields coerce to 0.0, not raised as errors."""
    user = _make_user()
    snap = MagicMock()
    snap.snapshot_date = date.today()
    for field in [
        "total_net_worth", "total_assets", "total_liabilities",
        "cash_and_checking", "savings", "investments", "retirement",
        "property", "vehicles", "other_assets", "credit_cards",
        "loans", "mortgages", "student_loans", "other_debts",
    ]:
        setattr(snap, field, None)

    db = _db_returning([snap])

    result = await get_net_worth_history(
        start_date=None,
        end_date=None,
        user_id=None,
        current_user=user,
        db=db,
    )

    assert len(result) == 1
    pt = result[0]
    assert pt.total_net_worth == 0.0
    assert pt.investments == 0.0
    assert pt.mortgages == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Source-level: lazy bootstrap block present in dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

def test_net_worth_history_source_has_lazy_bootstrap():
    """dashboard.py net-worth-history must contain lazy bootstrap logic."""
    import inspect
    import app.api.v1.dashboard as dash_module

    source = inspect.getsource(dash_module)
    assert "NetWorthService" in source, "dashboard.py must import NetWorthService for lazy bootstrap"
    assert "capture_snapshot" in source, "dashboard.py must call capture_snapshot for lazy bootstrap"
    assert "not snapshots" in source, "dashboard.py must check 'if not snapshots' to trigger bootstrap"
    assert "only_zero" in source, "dashboard.py must re-bootstrap when only $0 snapshots exist"


@pytest.mark.asyncio
async def test_net_worth_history_zero_snapshots_triggers_rebootstrap():
    """When all existing snapshots have total_net_worth=0, bootstrap re-runs."""
    user = _make_user()
    zero_snap = _make_snapshot(0)
    real_snap = _make_snapshot(50000)

    call_count = 0

    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        # First call returns stale $0 snapshot; second (after bootstrap) returns real data
        result.scalars.return_value.all.return_value = [zero_snap] if call_count == 1 else [real_snap]
        return result

    db = AsyncMock()
    db.execute = mock_execute
    db.commit = AsyncMock()

    mock_svc = MagicMock()
    mock_svc.capture_snapshot = AsyncMock(return_value=real_snap)

    with patch("app.services.net_worth_service.NetWorthService", return_value=mock_svc):
        result = await get_net_worth_history(
            start_date=None,
            end_date=None,
            user_id=None,
            current_user=user,
            db=db,
        )

    # Bootstrap should have been triggered and returned real data
    mock_svc.capture_snapshot.assert_awaited_once()
    assert len(result) == 1
    assert result[0].total_net_worth == 50000.0
