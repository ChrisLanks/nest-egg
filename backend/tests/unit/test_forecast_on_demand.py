"""Tests for on-demand recurring detection and thundering herd prevention in forecast."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.account import Account, AccountType
from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction
from app.services.forecast_service import ForecastService


def _make_db_with_account():
    """Return (db, account_id) with a mock CHECKING account."""
    checking = MagicMock(spec=Account)
    checking.id = uuid4()
    checking.account_type = AccountType.CHECKING
    checking.is_active = True
    checking.vesting_schedule = None
    checking.include_in_networth = True
    checking.company_status = None

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [checking]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock

    db = AsyncMock()
    db.execute.return_value = result_mock
    return db, checking.id


@pytest.mark.unit
class TestOnDemandDetection:
    """On-demand detection triggers when no recurring transactions exist."""

    @pytest.mark.asyncio
    async def test_detection_runs_when_no_recurring_exist(self):
        """detect_recurring_patterns is called when get_recurring_transactions returns []."""
        org_id = uuid4()
        db, _ = _make_db_with_account()

        with (
            patch.object(ForecastService, "_get_total_balance", new_callable=AsyncMock, return_value=Decimal("5000")),
            patch("app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                  new_callable=AsyncMock, return_value=[]),
            patch("app.services.forecast_service.RecurringDetectionService.detect_recurring_patterns",
                  new_callable=AsyncMock, return_value=[]) as mock_detect,
            patch("app.services.forecast_service.cache.setnx_with_ttl", new=AsyncMock(return_value=True)),
            patch("app.services.forecast_service.cache.delete", new=AsyncMock()),
            patch("app.services.forecast_service.cache.get", new=AsyncMock(return_value=None)),
            patch("app.services.forecast_service.cache.setex", new=AsyncMock()),
        ):
            await ForecastService.generate_forecast(db, org_id, days_ahead=5)

        mock_detect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_detection_skipped_when_recurring_exist(self):
        """detect_recurring_patterns is NOT called when patterns already exist."""
        org_id = uuid4()
        db, account_id = _make_db_with_account()

        pattern = MagicMock()
        pattern.account_id = account_id
        pattern.merchant_name = "Netflix"
        pattern.average_amount = Decimal("-15.99")
        pattern.frequency = RecurringFrequency.MONTHLY
        pattern.next_expected_date = date.today()
        pattern.category = None
        pattern.label = None
        pattern.account = None

        with (
            patch.object(ForecastService, "_get_total_balance", new_callable=AsyncMock, return_value=Decimal("5000")),
            patch("app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                  new_callable=AsyncMock, return_value=[pattern]),
            patch("app.services.forecast_service.RecurringDetectionService.detect_recurring_patterns",
                  new_callable=AsyncMock) as mock_detect,
            patch("app.services.forecast_service.cache.get", new=AsyncMock(return_value=None)),
            patch("app.services.forecast_service.cache.setex", new=AsyncMock()),
        ):
            await ForecastService.generate_forecast(db, org_id, days_ahead=5)

        mock_detect.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_re_fetches_after_detection(self):
        """get_recurring_transactions is called twice: before and after detection."""
        org_id = uuid4()
        db, _ = _make_db_with_account()

        call_count = 0

        async def get_recurring_side(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return []

        with (
            patch.object(ForecastService, "_get_total_balance", new_callable=AsyncMock, return_value=Decimal("1000")),
            patch("app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                  side_effect=get_recurring_side),
            patch("app.services.forecast_service.RecurringDetectionService.detect_recurring_patterns",
                  new_callable=AsyncMock, return_value=[]),
            patch("app.services.forecast_service.cache.setnx_with_ttl", new=AsyncMock(return_value=True)),
            patch("app.services.forecast_service.cache.delete", new=AsyncMock()),
            patch("app.services.forecast_service.cache.get", new=AsyncMock(return_value=None)),
            patch("app.services.forecast_service.cache.setex", new=AsyncMock()),
        ):
            await ForecastService.generate_forecast(db, org_id, days_ahead=5)

        assert call_count == 2  # once before, once after detection


@pytest.mark.unit
class TestThunderingHerdPrevention:
    """Distributed lock prevents concurrent requests from all running detection."""

    @pytest.mark.asyncio
    async def test_detection_skipped_when_lock_not_acquired(self):
        """When setnx_with_ttl returns False (lock held), detection is NOT run."""
        org_id = uuid4()
        db, _ = _make_db_with_account()

        with (
            patch.object(ForecastService, "_get_total_balance", new_callable=AsyncMock, return_value=Decimal("5000")),
            patch("app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                  new_callable=AsyncMock, return_value=[]),
            patch("app.services.forecast_service.RecurringDetectionService.detect_recurring_patterns",
                  new_callable=AsyncMock) as mock_detect,
            patch("app.services.forecast_service.cache.setnx_with_ttl", new=AsyncMock(return_value=False)),
            patch("app.services.forecast_service.cache.get", new=AsyncMock(return_value=None)),
            patch("app.services.forecast_service.cache.setex", new=AsyncMock()),
        ):
            result = await ForecastService.generate_forecast(db, org_id, days_ahead=5)

        mock_detect.assert_not_awaited()
        # Still returns a valid balance-only forecast
        assert len(result) == 6
        assert result[0]["projected_balance"] == 5000.0

    @pytest.mark.asyncio
    async def test_lock_uses_org_scoped_key(self):
        """The lock key is scoped to the organization to avoid cross-org contention."""
        org_id = uuid4()
        db, _ = _make_db_with_account()

        captured_key = []

        async def fake_setnx(key, ttl):
            captured_key.append(key)
            return True

        with (
            patch.object(ForecastService, "_get_total_balance", new_callable=AsyncMock, return_value=Decimal("0")),
            patch("app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                  new_callable=AsyncMock, return_value=[]),
            patch("app.services.forecast_service.RecurringDetectionService.detect_recurring_patterns",
                  new_callable=AsyncMock, return_value=[]),
            patch("app.services.forecast_service.cache.setnx_with_ttl", side_effect=fake_setnx),
            patch("app.services.forecast_service.cache.delete", new=AsyncMock()),
            patch("app.services.forecast_service.cache.get", new=AsyncMock(return_value=None)),
            patch("app.services.forecast_service.cache.setex", new=AsyncMock()),
        ):
            await ForecastService.generate_forecast(db, org_id, days_ahead=5)

        assert len(captured_key) == 1
        assert str(org_id) in captured_key[0]

    @pytest.mark.asyncio
    async def test_lock_released_on_detection_success(self):
        """cache.delete is called to release the lock after successful detection."""
        org_id = uuid4()
        db, _ = _make_db_with_account()

        mock_delete = AsyncMock()

        with (
            patch.object(ForecastService, "_get_total_balance", new_callable=AsyncMock, return_value=Decimal("0")),
            patch("app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                  new_callable=AsyncMock, return_value=[]),
            patch("app.services.forecast_service.RecurringDetectionService.detect_recurring_patterns",
                  new_callable=AsyncMock, return_value=[]),
            patch("app.services.forecast_service.cache.setnx_with_ttl", new=AsyncMock(return_value=True)),
            patch("app.services.forecast_service.cache.delete", new=mock_delete),
            patch("app.services.forecast_service.cache.get", new=AsyncMock(return_value=None)),
            patch("app.services.forecast_service.cache.setex", new=AsyncMock()),
        ):
            await ForecastService.generate_forecast(db, org_id, days_ahead=5)

        mock_delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lock_released_even_when_detection_fails(self):
        """Lock is released via finally even if detect_recurring_patterns raises."""
        org_id = uuid4()
        db, _ = _make_db_with_account()

        mock_delete = AsyncMock()

        with (
            patch.object(ForecastService, "_get_total_balance", new_callable=AsyncMock, return_value=Decimal("0")),
            patch("app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                  new_callable=AsyncMock, return_value=[]),
            patch("app.services.forecast_service.RecurringDetectionService.detect_recurring_patterns",
                  new_callable=AsyncMock, side_effect=RuntimeError("DB error")),
            patch("app.services.forecast_service.cache.setnx_with_ttl", new=AsyncMock(return_value=True)),
            patch("app.services.forecast_service.cache.delete", new=mock_delete),
            patch("app.services.forecast_service.cache.get", new=AsyncMock(return_value=None)),
            patch("app.services.forecast_service.cache.setex", new=AsyncMock()),
        ):
            with pytest.raises(RuntimeError, match="DB error"):
                await ForecastService.generate_forecast(db, org_id, days_ahead=5)

        mock_delete.assert_awaited_once()


@pytest.mark.unit
class TestCacheSetnxWithTtl:
    """Tests for cache.setnx_with_ttl distributed lock primitive."""

    @pytest.mark.asyncio
    async def test_returns_true_when_lock_acquired(self):
        """Returns True when Redis SET NX EX succeeds (key was absent)."""
        from app.core import cache

        mock_client = AsyncMock()
        mock_client.set.return_value = "OK"

        original = cache.redis_client
        try:
            cache.redis_client = mock_client
            result = await cache.setnx_with_ttl("test:lock", 60)
        finally:
            cache.redis_client = original

        assert result is True
        mock_client.set.assert_awaited_once_with("test:lock", 1, nx=True, ex=60)

    @pytest.mark.asyncio
    async def test_returns_false_when_lock_already_held(self):
        """Returns False when Redis SET NX EX returns None (key already exists)."""
        from app.core import cache

        mock_client = AsyncMock()
        mock_client.set.return_value = None  # Redis returns None when NX fails

        original = cache.redis_client
        try:
            cache.redis_client = mock_client
            result = await cache.setnx_with_ttl("test:lock", 60)
        finally:
            cache.redis_client = original

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_redis_unavailable(self):
        """Falls back to True (lock always acquired) when Redis is None."""
        from app.core import cache

        original = cache.redis_client
        try:
            cache.redis_client = None
            result = await cache.setnx_with_ttl("test:lock", 60)
        finally:
            cache.redis_client = original

        assert result is True  # Single-process fallback

    @pytest.mark.asyncio
    async def test_returns_false_on_redis_error(self):
        """Returns False (conservatively skips lock) on Redis connection error."""
        from app.core import cache

        mock_client = AsyncMock()
        mock_client.set.side_effect = Exception("Connection refused")

        original = cache.redis_client
        try:
            cache.redis_client = mock_client
            result = await cache.setnx_with_ttl("test:lock", 60)
        finally:
            cache.redis_client = original

        assert result is False
