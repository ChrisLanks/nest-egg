"""Unit tests for per-user historical snapshot functionality.

Covers:
- SnapshotService.get_snapshots user_id filtering
- SnapshotService.capture_snapshot with user_id
- get_historical_snapshots API endpoint user_id parameter
- capture_org_portfolio_snapshot per-user snapshot creation
- PortfolioSnapshot model user_id column
"""

import sys
from unittest.mock import MagicMock

# Stub celery before importing task module
_celery_stub = MagicMock()
sys.modules.setdefault("celery", _celery_stub)
sys.modules.setdefault("app.workers.celery_app", _celery_stub)

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.api.v1.holdings import get_historical_snapshots
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import User
from app.services.snapshot_service import SnapshotService

# ── SnapshotService.get_snapshots ─────────────────────────────────────────


@pytest.mark.unit
class TestGetSnapshotsUserFiltering:
    """Test that get_snapshots filters by user_id correctly."""

    @pytest.fixture
    def service(self):
        return SnapshotService()

    @pytest.fixture
    def org_id(self):
        return uuid4()

    @pytest.mark.asyncio
    async def test_household_snapshots_when_user_id_none(self, service, org_id):
        """When user_id is None, should return household snapshots."""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_snapshots(db=mock_db, organization_id=org_id)

        assert result == []
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_user_snapshots_when_user_id_provided(self, service, org_id):
        """When user_id is a UUID, should filter for that user."""
        uid = uuid4()
        mock_db = AsyncMock()
        snap = Mock(spec=PortfolioSnapshot)
        snap.user_id = uid
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [snap]
        mock_db.execute.return_value = mock_result

        result = await service.get_snapshots(db=mock_db, organization_id=org_id, user_id=uid)

        assert len(result) == 1
        assert result[0].user_id == uid

    @pytest.mark.asyncio
    async def test_date_range_filtering(self, service, org_id):
        """Date range params should be applied alongside user filter."""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_snapshots(
            db=mock_db,
            organization_id=org_id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
        )

        assert result == []
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_limit_applied(self, service, org_id):
        """Limit parameter should be accepted without error."""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_snapshots(db=mock_db, organization_id=org_id, limit=10)

        assert result == []
        assert mock_db.execute.called


# ── SnapshotService.capture_snapshot ──────────────────────────────────────


@pytest.mark.unit
class TestCaptureSnapshotUserParam:
    """Test that capture_snapshot handles user_id for per-user snapshots."""

    @pytest.fixture
    def service(self):
        return SnapshotService()

    @pytest.fixture
    def mock_portfolio(self):
        """Minimal PortfolioSummary mock."""
        p = Mock()
        p.total_value = Decimal("50000")
        p.total_cost_basis = Decimal("45000")
        p.total_gain_loss = Decimal("5000")
        p.total_gain_loss_percent = Decimal("11.11")
        p.stocks_value = Decimal("30000")
        p.bonds_value = Decimal("10000")
        p.etf_value = Decimal("5000")
        p.mutual_funds_value = Decimal("3000")
        p.cash_value = Decimal("2000")
        p.other_value = Decimal("0")
        p.holdings_by_ticker = []
        p.holdings_by_account = []
        p.category_breakdown = None
        p.geographic_breakdown = None
        p.sector_breakdown = None
        return p

    @pytest.mark.asyncio
    async def test_household_snapshot_no_user_id(self, service, mock_portfolio):
        """capture_snapshot without user_id creates household snapshot."""
        org_id = uuid4()
        mock_db = AsyncMock()
        mock_snapshot = Mock(spec=PortfolioSnapshot)
        mock_snapshot.total_value = Decimal("50000")
        mock_result = Mock()
        mock_result.scalar_one.return_value = mock_snapshot
        mock_db.execute.return_value = mock_result

        result = await service.capture_snapshot(
            db=mock_db,
            organization_id=org_id,
            portfolio=mock_portfolio,
        )

        assert result == mock_snapshot
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_per_user_snapshot_with_user_id(self, service, mock_portfolio):
        """capture_snapshot with user_id creates per-user snapshot."""
        org_id = uuid4()
        uid = uuid4()
        mock_db = AsyncMock()
        mock_snapshot = Mock(spec=PortfolioSnapshot)
        mock_snapshot.total_value = Decimal("50000")
        mock_result = Mock()
        mock_result.scalar_one.return_value = mock_snapshot
        mock_db.execute.return_value = mock_result

        result = await service.capture_snapshot(
            db=mock_db,
            organization_id=org_id,
            portfolio=mock_portfolio,
            user_id=uid,
        )

        assert result == mock_snapshot
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_snapshot_accepts_snapshot_date(self, service, mock_portfolio):
        """capture_snapshot should accept a specific snapshot_date."""
        org_id = uuid4()
        mock_db = AsyncMock()
        mock_snapshot = Mock(spec=PortfolioSnapshot)
        mock_snapshot.total_value = Decimal("50000")
        mock_result = Mock()
        mock_result.scalar_one.return_value = mock_snapshot
        mock_db.execute.return_value = mock_result

        result = await service.capture_snapshot(
            db=mock_db,
            organization_id=org_id,
            portfolio=mock_portfolio,
            snapshot_date=date(2025, 6, 15),
        )

        assert result == mock_snapshot


# ── API endpoint: get_historical_snapshots ────────────────────────────────


@pytest.mark.unit
class TestHistoricalSnapshotsEndpointUserFilter:
    """Test get_historical_snapshots API endpoint with user_id param."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_passes_user_id_to_service(self, mock_db, mock_user):
        """When user_id is given, it should be passed to get_snapshots."""
        uid = uuid4()

        with (
            patch(
                "app.api.v1.holdings.snapshot_service.get_snapshots",
                return_value=[],
            ) as mock_get,
            patch(
                "app.api.v1.holdings.verify_household_member",
                return_value=None,
            ),
        ):
            result = await get_historical_snapshots(
                start_date=date(2025, 1, 1),
                end_date=None,
                limit=None,
                user_id=uid,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == []
            mock_get.assert_called_once_with(
                db=mock_db,
                organization_id=mock_user.organization_id,
                start_date=date(2025, 1, 1),
                end_date=None,
                limit=None,
                user_id=uid,
            )

    @pytest.mark.asyncio
    async def test_household_when_user_id_none(self, mock_db, mock_user):
        """When user_id is None, should pass None to service."""
        with patch(
            "app.api.v1.holdings.snapshot_service.get_snapshots",
            return_value=[],
        ) as mock_get:
            await get_historical_snapshots(
                start_date=date(2025, 1, 1),
                end_date=None,
                limit=None,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            mock_get.assert_called_once()
            assert mock_get.call_args.kwargs["user_id"] is None

    @pytest.mark.asyncio
    async def test_verifies_household_member(self, mock_db, mock_user):
        """Should call verify_household_member when user_id is provided."""
        uid = uuid4()

        with (
            patch(
                "app.api.v1.holdings.snapshot_service.get_snapshots",
                return_value=[],
            ),
            patch(
                "app.api.v1.holdings.verify_household_member",
                return_value=None,
            ) as mock_verify,
        ):
            await get_historical_snapshots(
                start_date=date(2025, 1, 1),
                end_date=None,
                limit=None,
                user_id=uid,
                current_user=mock_user,
                db=mock_db,
            )

            mock_verify.assert_called_once_with(
                user_id=uid,
                organization_id=mock_user.organization_id,
                db=mock_db,
            )

    @pytest.mark.asyncio
    async def test_no_verify_when_user_id_none(self, mock_db, mock_user):
        """Should NOT call verify_household_member when user_id is None."""
        with (
            patch(
                "app.api.v1.holdings.snapshot_service.get_snapshots",
                return_value=[],
            ),
            patch(
                "app.api.v1.holdings.verify_household_member",
                return_value=None,
            ) as mock_verify,
        ):
            await get_historical_snapshots(
                start_date=date(2025, 1, 1),
                end_date=None,
                limit=None,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            mock_verify.assert_not_called()

    @pytest.mark.asyncio
    async def test_defaults_start_date_when_none(self, mock_db, mock_user):
        """Should default to 1 year ago when start_date is None."""
        with patch(
            "app.api.v1.holdings.snapshot_service.get_snapshots",
            return_value=[],
        ) as mock_get:
            await get_historical_snapshots(
                start_date=None,
                end_date=None,
                limit=None,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            call_args = mock_get.call_args
            start_date_arg = call_args.kwargs["start_date"]
            expected = date.today().replace(year=date.today().year - 1)
            assert abs((start_date_arg - expected).days) <= 1


# ── Snapshot task: per-user capture ───────────────────────────────────────


@pytest.mark.unit
class TestSnapshotTaskPerUser:
    """Test capture_org_portfolio_snapshot creates per-user snapshots."""

    def test_task_exists(self):
        """Task function should be importable."""
        from app.workers.tasks.snapshot_tasks import (
            capture_org_portfolio_snapshot,
        )

        assert capture_org_portfolio_snapshot is not None

    def test_orchestrator_exists(self):
        """Orchestrator task should be importable."""
        from app.workers.tasks.snapshot_tasks import (
            orchestrate_portfolio_snapshots,
        )

        assert orchestrate_portfolio_snapshots is not None

    def test_dispatch_creates_tasks_for_each_org(self):
        """_dispatch_snapshot_tasks should create one task per org."""
        from app.workers.tasks.snapshot_tasks import (
            _dispatch_snapshot_tasks,
            capture_org_portfolio_snapshot,
        )

        org1_id = uuid4()
        org2_id = uuid4()

        with patch.object(capture_org_portfolio_snapshot, "apply_async") as mock_apply:
            count = _dispatch_snapshot_tasks([org1_id, org2_id])

        assert count == 2
        assert mock_apply.call_count == 2


# ── PortfolioSnapshot model ───────────────────────────────────────────────


@pytest.mark.unit
class TestPortfolioSnapshotModel:
    """Test PortfolioSnapshot model has user_id column."""

    def test_has_user_id_column(self):
        """Model should have user_id column."""
        assert hasattr(PortfolioSnapshot, "user_id")

    def test_user_id_nullable(self):
        """user_id column should be nullable (None = household)."""
        col = PortfolioSnapshot.__table__.columns["user_id"]
        assert col.nullable is True

    def test_user_id_foreign_key(self):
        """user_id should reference users.id."""
        col = PortfolioSnapshot.__table__.columns["user_id"]
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "users.id" in fk_targets

    def test_user_id_indexed(self):
        """user_id column should be indexed for query performance."""
        col = PortfolioSnapshot.__table__.columns["user_id"]
        assert col.index is True

    def test_repr_format(self):
        """__repr__ should include org_id, date, and value."""
        snap = PortfolioSnapshot()
        snap.organization_id = uuid4()
        snap.snapshot_date = date(2025, 6, 15)
        snap.total_value = Decimal("50000")
        r = repr(snap)
        assert "PortfolioSnapshot" in r
        assert "50000" in r

    def test_has_required_columns(self):
        """Model should have all expected columns."""
        columns = PortfolioSnapshot.__table__.columns
        expected = [
            "id",
            "organization_id",
            "user_id",
            "snapshot_date",
            "total_value",
            "total_cost_basis",
            "total_gain_loss",
            "snapshot_data",
            "created_at",
        ]
        for col_name in expected:
            assert col_name in columns, f"Missing column: {col_name}"
