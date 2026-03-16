"""Unit tests for holdings_tasks — enrich metadata, capture snapshots, update prices."""

import sys
from unittest.mock import MagicMock

# Stub celery before importing task module
_celery_stub = MagicMock()
sys.modules.setdefault("celery", _celery_stub)
sys.modules.setdefault("app.workers.celery_app", _celery_stub)

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.workers.tasks.holdings_tasks import (
    _capture_snapshots_async,
    _enrich_metadata_async,
    _update_prices_async,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _mock_holding(ticker="AAPL", org_id=None, price_as_of=None):
    h = Mock()
    h.id = uuid4()
    h.ticker = ticker
    h.organization_id = org_id or uuid4()
    h.name = None
    h.asset_type = None
    h.asset_class = None
    h.market_cap = None
    h.sector = None
    h.industry = None
    h.country = None
    h.price_as_of = price_as_of
    return h


def _mock_metadata(
    name="Apple Inc",
    asset_type="stock",
    asset_class="domestic",
    market_cap="large",
    sector="Technology",
    industry="Consumer Electronics",
    country="US",
):
    m = Mock()
    m.name = name
    m.asset_type = asset_type
    m.asset_class = asset_class
    m.market_cap = market_cap
    m.sector = sector
    m.industry = industry
    m.country = country
    return m


# ── _enrich_metadata_async ───────────────────────────────────────────────────


@pytest.mark.unit
class TestEnrichMetadataAsync:
    """Test holdings metadata enrichment."""

    @pytest.mark.asyncio
    async def test_no_holdings_returns_early(self):
        """If no holdings exist, exits early."""
        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_enriches_holdings_with_metadata(self):
        """Holdings are enriched with provider metadata."""
        org_id = uuid4()
        h = _mock_holding("AAPL", org_id)
        metadata = _mock_metadata()

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        mock_provider = AsyncMock()
        mock_provider.get_holding_metadata = AsyncMock(return_value=metadata)
        mock_provider.get_provider_name.return_value = "test_provider"

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handles_provider_error_gracefully(self):
        """Provider errors for individual tickers don't crash the task."""
        org_id = uuid4()
        h = _mock_holding("BAD", org_id)

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        mock_provider = AsyncMock()
        mock_provider.get_holding_metadata = AsyncMock(side_effect=Exception("API error"))
        mock_provider.get_provider_name.return_value = "test_provider"

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        # Should still commit (with 0 enriched, 1 failed)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_metadata_with_all_none_skips_update(self):
        """When provider returns all None fields, only updated_at is set."""
        org_id = uuid4()
        h = _mock_holding("XYZ", org_id)
        metadata = _mock_metadata(
            name=None,
            asset_type=None,
            asset_class=None,
            market_cap=None,
            sector=None,
            industry=None,
            country=None,
        )

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        mock_provider = AsyncMock()
        mock_provider.get_holding_metadata = AsyncMock(return_value=metadata)
        mock_provider.get_provider_name.return_value = "test_provider"

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_db_error_raises(self):
        """DB-level errors propagate."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB down")

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            with pytest.raises(Exception, match="DB down"):
                await _enrich_metadata_async()


# ── _update_prices_async ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpdatePricesAsync:
    """Test holdings price update task."""

    @pytest.mark.asyncio
    async def test_no_stale_holdings_returns_early(self):
        """If all holdings are fresh, exits early."""
        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _update_prices_async()

        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_updates_stale_holdings(self):
        """Stale holdings get their prices updated."""
        stale_time = datetime.now(timezone.utc) - timedelta(hours=12)
        h = _mock_holding("AAPL", price_as_of=stale_time)

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock

        update_result = Mock()
        update_result.rowcount = 1
        mock_db.execute.side_effect = [result_mock, update_result]

        quote = Mock()
        quote.price = Decimal("150.00")
        mock_provider = AsyncMock()
        mock_provider.get_quotes_batch = AsyncMock(return_value={"AAPL": quote})
        mock_provider.get_provider_name.return_value = "test_provider"

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _update_prices_async()

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_quote_skipped(self):
        """Tickers with no quote available are skipped."""
        h = _mock_holding("UNKN")

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        mock_provider = AsyncMock()
        mock_provider.get_quotes_batch = AsyncMock(return_value={})
        mock_provider.get_provider_name.return_value = "test_provider"

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _update_prices_async()

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_db_error_raises(self):
        """DB-level errors propagate."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB down")

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            with pytest.raises(Exception, match="DB down"):
                await _update_prices_async()


# ── _capture_snapshots_async ─────────────────────────────────────────────────


@pytest.mark.unit
class TestCaptureSnapshotsAsync:
    """Test holdings snapshot capture."""

    @pytest.mark.asyncio
    async def test_no_orgs_returns_early(self):
        """If no orgs exist, exits cleanly."""
        mock_db = AsyncMock()
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _capture_snapshots_async()

    @pytest.mark.asyncio
    async def test_db_error_raises(self):
        """DB-level errors propagate."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB down")

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            with pytest.raises(Exception, match="DB down"):
                await _capture_snapshots_async()


# ── Celery task wrapper tests ──────────────────────────────────────────────


@pytest.mark.unit
class TestCeleryTaskWrappers:
    """Test that task wrappers call asyncio.run."""

    def test_enrich_task_calls_asyncio_run(self):
        from app.workers.tasks.holdings_tasks import enrich_holdings_metadata_task

        with patch("app.workers.tasks.holdings_tasks.asyncio.run") as mock_run:
            enrich_holdings_metadata_task()
            mock_run.assert_called_once()

    def test_snapshot_task_calls_asyncio_run(self):
        from app.workers.tasks.holdings_tasks import capture_daily_holdings_snapshot_task

        with patch("app.workers.tasks.holdings_tasks.asyncio.run") as mock_run:
            capture_daily_holdings_snapshot_task()
            mock_run.assert_called_once()

    def test_prices_task_calls_asyncio_run(self):
        from app.workers.tasks.holdings_tasks import update_holdings_prices_task

        with patch("app.workers.tasks.holdings_tasks.asyncio.run") as mock_run:
            update_holdings_prices_task()
            mock_run.assert_called_once()


@pytest.mark.unit
class TestUpdatePricesPerTickerError:
    """Test per-ticker error handling in price updates."""

    @pytest.mark.asyncio
    async def test_handles_update_error_per_ticker(self):
        """Should continue with other tickers when one fails to update."""
        h1 = _mock_holding("AAPL")
        h2 = _mock_holding("MSFT")

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h1, h2]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock

        update_success = Mock()
        update_success.rowcount = 1

        mock_db.execute.side_effect = [result_mock, Exception("Update failed"), update_success]

        quote = Mock()
        quote.price = Decimal("150.00")
        mock_provider = AsyncMock()
        mock_provider.get_quotes_batch = AsyncMock(return_value={"AAPL": quote, "MSFT": quote})
        mock_provider.get_provider_name.return_value = "test_provider"

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _update_prices_async()

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_existing_snapshot_skipped(self):
        """Orgs with existing today's snapshot are skipped."""
        org_id = uuid4()
        mock_db = AsyncMock()

        call_count = 0

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = Mock()
            if call_count == 1:
                result.all.return_value = [(org_id,)]
            elif call_count == 2:
                # Existing snapshot found
                result.scalar_one_or_none.return_value = Mock()
            return result

        mock_db.execute.side_effect = execute_side_effect

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _capture_snapshots_async()

    @pytest.mark.asyncio
    async def test_no_users_for_org_skipped(self):
        """Orgs with no users are skipped."""
        org_id = uuid4()
        mock_db = AsyncMock()

        call_count = 0

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = Mock()
            if call_count == 1:
                result.all.return_value = [(org_id,)]
            elif call_count == 2:
                result.scalar_one_or_none.return_value = None  # No existing snapshot
            elif call_count == 3:
                result.scalar_one_or_none.return_value = None  # No user found
            return result

        mock_db.execute.side_effect = execute_side_effect

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _capture_snapshots_async()

    @pytest.mark.asyncio
    async def test_successful_snapshot_capture(self):
        """Successful snapshot creation for an org."""
        org_id = uuid4()
        mock_user = Mock()
        mock_user.organization_id = org_id
        mock_portfolio = Mock()
        mock_snapshot = Mock()
        mock_snapshot.total_value = Decimal("100000")

        mock_db = AsyncMock()
        call_count = 0

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = Mock()
            if call_count == 1:
                result.all.return_value = [(org_id,)]
            elif call_count == 2:
                result.scalar_one_or_none.return_value = None  # No existing snapshot
            elif call_count == 3:
                result.scalar_one_or_none.return_value = mock_user
            return result

        mock_db.execute.side_effect = execute_side_effect

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch("app.workers.tasks.holdings_tasks.snapshot_service") as mock_snap_svc,
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_snap_svc.capture_snapshot = AsyncMock(return_value=mock_snapshot)

            with patch(
                "app.api.v1.holdings.get_portfolio_summary",
                new_callable=AsyncMock,
                return_value=mock_portfolio,
            ):
                await _capture_snapshots_async()

    @pytest.mark.asyncio
    async def test_per_org_error_continues(self):
        """Error for one org doesn't stop others."""
        org1, org2 = uuid4(), uuid4()
        mock_db = AsyncMock()
        call_count = 0

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = Mock()
            if call_count == 1:
                result.all.return_value = [(org1,), (org2,)]
            elif call_count == 2:
                raise Exception("Snapshot error for org1")
            elif call_count == 3:
                # org2 already has snapshot
                result.scalar_one_or_none.return_value = Mock()
            return result

        mock_db.execute.side_effect = execute_side_effect

        with patch("app.workers.utils.get_celery_session") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _capture_snapshots_async()
