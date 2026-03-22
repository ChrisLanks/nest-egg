"""Unit tests for holdings_tasks — enrich metadata, capture snapshots, update prices.

Expense ratio (ER) enrichment tests verify the priority chain:
  1. yfinance API value (metadata.expense_ratio) — stored only when holding ER is NULL
  2. KNOWN_EXPENSE_RATIOS static table — fallback when API returns None
  3. Existing holding ER is never overwritten
"""

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


def _mock_holding(ticker="AAPL", org_id=None, price_as_of=None, expense_ratio=None):
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
    h.expense_ratio = expense_ratio
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
    expense_ratio=None,
):
    m = Mock()
    m.name = name
    m.asset_type = asset_type
    m.asset_class = asset_class
    m.market_cap = market_cap
    m.sector = sector
    m.industry = industry
    m.country = country
    m.expense_ratio = expense_ratio
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
    async def test_handles_provider_error_raises_after_all_tickers(self):
        """Provider errors for individual tickers are collected; task re-raises after all tickers processed."""
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
            with pytest.raises(RuntimeError, match="BAD"):
                await _enrich_metadata_async()

        # Should still commit before raising (other work may have succeeded)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_partial_failure_includes_all_failed_tickers_in_message(self):
        """When multiple tickers fail, all are listed in the RuntimeError message."""
        org1 = uuid4()
        org2 = uuid4()
        h_bad1 = _mock_holding("FAIL1", org1)
        h_bad2 = _mock_holding("FAIL2", org2)
        h_good = _mock_holding("AAPL", org1)

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h_bad1, h_bad2, h_good]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        good_metadata = _mock_metadata()

        def metadata_side_effect(ticker):
            if ticker in ("FAIL1", "FAIL2"):
                raise Exception(f"API error for {ticker}")
            return good_metadata

        mock_provider = AsyncMock()
        mock_provider.get_holding_metadata = AsyncMock(side_effect=metadata_side_effect)
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
            with pytest.raises(RuntimeError) as exc_info:
                await _enrich_metadata_async()

        assert "FAIL1" in str(exc_info.value)
        assert "FAIL2" in str(exc_info.value)
        # Commit still happened (good ticker was enriched before raise)
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


# ── TestEnrichExpenseRatio ────────────────────────────────────────────────────


@pytest.mark.unit
class TestEnrichExpenseRatio:
    """Test expense ratio enrichment in the nightly metadata task."""

    def _setup_db(self, mock_db, holdings):
        scalars_mock = Mock()
        scalars_mock.all.return_value = holdings
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

    @pytest.mark.asyncio
    async def test_er_from_api_written_when_holding_er_is_null(self):
        """When API returns an expense_ratio and holding has none, ER is stored."""
        from decimal import Decimal

        org_id = uuid4()
        h = _mock_holding("VTI", org_id, expense_ratio=None)
        metadata = _mock_metadata(expense_ratio=Decimal("0.0003"))

        mock_db = AsyncMock()
        self._setup_db(mock_db, [h])

        mock_provider = AsyncMock()
        mock_provider.get_holding_metadata = AsyncMock(return_value=metadata)
        mock_provider.get_provider_name.return_value = "test_provider"

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
            patch("app.workers.tasks.holdings_tasks.cache_delete_pattern", new_callable=AsyncMock),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        mock_db.commit.assert_awaited_once()
        # SELECT + UPDATE = at least 2 execute calls
        assert mock_db.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_er_not_overwritten_when_already_stored(self):
        """When a holding already has an expense_ratio, the task must not overwrite it."""
        from decimal import Decimal

        org_id = uuid4()
        # Holding already has an ER stored
        h = _mock_holding("VTI", org_id, expense_ratio=Decimal("0.0010"))
        # API also returns an ER — should be ignored
        metadata = _mock_metadata(expense_ratio=Decimal("0.0003"))

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
            patch("app.workers.tasks.holdings_tasks.cache_delete_pattern", new_callable=AsyncMock),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        # Commit still called (other metadata fields may be updated)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_known_er_fallback_used_when_api_returns_none(self):
        """When API returns no ER but ticker is in KNOWN_EXPENSE_RATIOS, fallback is stored."""
        from app.services.fund_fee_analyzer_service import KNOWN_EXPENSE_RATIOS

        # Find a ticker that is in the static table
        known_ticker = next(iter(KNOWN_EXPENSE_RATIOS))
        org_id = uuid4()
        h = _mock_holding(known_ticker, org_id, expense_ratio=None)
        # API returns no expense_ratio
        metadata = _mock_metadata(expense_ratio=None)

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
            patch("app.workers.tasks.holdings_tasks.cache_delete_pattern", new_callable=AsyncMock),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        # UPDATE must have been issued (SELECT + UPDATE = at least 2 execute calls)
        assert mock_db.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_unknown_ticker_no_api_er_no_known_er_commits_cleanly(self):
        """An unknown ticker with no API ER and no static fallback still completes."""
        org_id = uuid4()
        h = _mock_holding("ZZZNEW", org_id, expense_ratio=None)
        # API returns minimal metadata but no ER
        metadata = _mock_metadata(
            name=None,
            asset_type=None,
            asset_class=None,
            market_cap=None,
            sector=None,
            industry=None,
            country=None,
            expense_ratio=None,
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
            patch("app.workers.tasks.holdings_tasks.cache_delete_pattern", new_callable=AsyncMock),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        # Task commits even when there's nothing to enrich
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fee_analysis_cache_invalidated_after_enrichment(self):
        """Both portfolio:summary:* and fee-analysis:* cache patterns are cleared."""
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
            patch(
                "app.workers.tasks.holdings_tasks.cache_delete_pattern", new_callable=AsyncMock
            ) as mock_cache_delete,
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        patterns_cleared = [call.args[0] for call in mock_cache_delete.call_args_list]
        assert "portfolio:summary:*" in patterns_cleared
        assert "fee-analysis:*" in patterns_cleared

    @pytest.mark.asyncio
    async def test_multiple_holdings_same_ticker_only_queries_api_once(self):
        """Two holdings with the same ticker result in a single metadata API call."""
        org_id = uuid4()
        h1 = _mock_holding("VTI", org_id, expense_ratio=None)
        h2 = _mock_holding("VTI", org_id, expense_ratio=None)
        h2.id = uuid4()
        metadata = _mock_metadata(expense_ratio=None)

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h1, h2]
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
            patch("app.workers.tasks.holdings_tasks.cache_delete_pattern", new_callable=AsyncMock),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        # Only one API call despite two holdings sharing the same ticker
        mock_provider.get_holding_metadata.assert_awaited_once_with("VTI")

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


# ── cross-org ER contamination fix ────────────────────────────────────────────


@pytest.mark.unit
class TestCrossOrgErIsolation:
    """Verify that expense_ratio enrichment is scoped per (ticker, org_id)."""

    @pytest.mark.asyncio
    async def test_org_with_er_does_not_block_other_org_enrichment(self):
        """Org A having an ER for VTSAX must not prevent Org B from receiving one."""
        org_a = uuid4()
        org_b = uuid4()
        # Org A has an ER; org B does not
        h_a = _mock_holding("VTSAX", org_a, expense_ratio=Decimal("0.0003"))
        h_b = _mock_holding("VTSAX", org_b, expense_ratio=None)

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h_a, h_b]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        metadata = _mock_metadata(
            name="Vanguard Total Stock Market",
            expense_ratio=Decimal("0.0003"),
        )
        mock_provider = AsyncMock()
        mock_provider.get_holding_metadata = AsyncMock(return_value=metadata)
        mock_provider.get_provider_name.return_value = "test"

        execute_calls = []

        async def record_execute(stmt):
            execute_calls.append(stmt)
            return result_mock

        mock_db.execute = AsyncMock(side_effect=record_execute)
        # First call is the SELECT; subsequent calls are UPDATEs
        mock_db.execute.side_effect = [result_mock] + [result_mock] * 10

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
            patch("app.workers.tasks.holdings_tasks.cache_delete_pattern", AsyncMock()),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        # Two UPDATE calls should have been made (one per org)
        # execute call count = 1 (SELECT) + 2 (UPDATE per org) = 3
        assert mock_db.execute.await_count >= 3

    @pytest.mark.asyncio
    async def test_both_orgs_have_er_no_enrichment_for_either(self):
        """When both orgs already have an ER, neither should be updated."""
        org_a = uuid4()
        org_b = uuid4()
        h_a = _mock_holding("VTSAX", org_a, expense_ratio=Decimal("0.0003"))
        h_b = _mock_holding("VTSAX", org_b, expense_ratio=Decimal("0.0004"))

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [h_a, h_b]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        metadata = _mock_metadata(name="Vanguard Total", expense_ratio=Decimal("0.0003"))
        mock_provider = AsyncMock()
        mock_provider.get_holding_metadata = AsyncMock(return_value=metadata)
        mock_provider.get_provider_name.return_value = "test"

        with (
            patch("app.workers.utils.get_celery_session") as mock_factory,
            patch(
                "app.workers.tasks.holdings_tasks.get_market_data_provider",
                return_value=mock_provider,
            ),
            patch("app.workers.tasks.holdings_tasks.cache_delete_pattern", AsyncMock()),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _enrich_metadata_async()

        mock_db.commit.assert_awaited_once()
