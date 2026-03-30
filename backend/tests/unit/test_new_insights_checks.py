"""Unit tests for the two new SmartInsightsService checks:

  - _check_spending_anomaly
  - _check_budget_overrun
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.smart_insights_service import (
    INSIGHT_BUDGET_OVERRUN,
    INSIGHT_SPENDING_ANOMALY,
    SmartInsightsService,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _svc():
    return SmartInsightsService(db=AsyncMock())


def _account_ids():
    return [uuid.uuid4()]


def _mock_execute(db: AsyncMock, rows: list):
    """Make db.execute return a result whose .all() yields rows."""
    result = MagicMock()
    result.all.return_value = rows
    db.execute = AsyncMock(return_value=result)
    return db


def _mock_execute_scalar(db: AsyncMock, value):
    """Make db.execute return a result whose .scalar() yields value."""
    result = MagicMock()
    result.scalar.return_value = value
    db.execute = AsyncMock(return_value=result)
    return db


def _row(merchant_name: str, total: float):
    r = MagicMock()
    r.merchant_name = merchant_name
    r.mtd_total = total
    r.hist_total = total
    return r


def _budget_row(name: str, amount: float, category_id=None, label_id=None):
    r = MagicMock()
    r.id = uuid.uuid4()
    r.name = name
    r.amount = amount
    r.category_id = category_id
    r.label_id = label_id
    return r


# ── TestCheckSpendingAnomaly ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCheckSpendingAnomaly:
    async def test_returns_none_when_no_account_ids(self):
        svc = _svc()
        result = await svc._check_spending_anomaly([])
        assert result is None

    async def test_returns_none_when_no_mtd_transactions(self):
        svc = _svc()
        # First execute (MTD) returns empty; second (hist) irrelevant
        mtd_result = MagicMock()
        mtd_result.all.return_value = []
        svc.db.execute = AsyncMock(return_value=mtd_result)

        result = await svc._check_spending_anomaly(_account_ids())
        assert result is None

    async def test_returns_none_when_no_anomaly(self):
        """Merchant MTD matches historical average — no anomaly."""
        svc = _svc()

        mtd_row = _row("Amazon", 100.0)
        hist_row = _row("Amazon", 300.0)  # hist_total over 3 months → avg 100/mo

        call_count = 0

        async def _execute(stmt, **kw):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [mtd_row]
            else:
                result.all.return_value = [hist_row]
            return result

        svc.db.execute = _execute
        result = await svc._check_spending_anomaly(_account_ids())
        assert result is None

    async def test_detects_anomaly_at_2x_multiplier(self):
        """MTD $200, avg $90 → ratio 2.2x, excess $110 ≥ $50 → fires."""
        svc = _svc()

        mtd_row = _row("Target", 200.0)
        # hist_total 270 over 3 months → avg 90/mo
        hist_row = _row("Target", 270.0)

        call_count = 0

        async def _execute(stmt, **kw):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [mtd_row]
            else:
                result.all.return_value = [hist_row]
            return result

        svc.db.execute = _execute
        result = await svc._check_spending_anomaly(_account_ids())
        assert result is not None
        assert result.type == INSIGHT_SPENDING_ANOMALY
        assert "Target" in result.title
        assert result.category == "spending"
        assert result.amount is not None
        assert result.amount > 0

    async def test_returns_none_when_excess_below_50(self):
        """MTD $60, avg $25 → ratio 2.4x, excess $35 < $50 → no fire."""
        svc = _svc()

        mtd_row = _row("Coffee Shop", 60.0)
        hist_row = _row("Coffee Shop", 75.0)  # avg 25/mo

        call_count = 0

        async def _execute(stmt, **kw):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [mtd_row]
            else:
                result.all.return_value = [hist_row]
            return result

        svc.db.execute = _execute
        result = await svc._check_spending_anomaly(_account_ids())
        assert result is None

    async def test_priority_is_high_at_5x(self):
        """Ratio ≥ 5x → high priority."""
        svc = _svc()

        # avg = 100/mo, mtd = 600 → ratio 6x, excess $500
        mtd_row = _row("Casino", 600.0)
        hist_row = _row("Casino", 300.0)  # avg 100/mo

        call_count = 0

        async def _execute(stmt, **kw):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [mtd_row]
            else:
                result.all.return_value = [hist_row]
            return result

        svc.db.execute = _execute
        result = await svc._check_spending_anomaly(_account_ids())
        assert result is not None
        assert result.priority == "high"

    async def test_priority_is_medium_at_2_to_5x(self):
        """Ratio between 2x and 5x → medium priority."""
        svc = _svc()

        # avg = 100/mo, mtd = 300 → ratio 3x, excess $200
        mtd_row = _row("Walmart", 300.0)
        hist_row = _row("Walmart", 300.0)  # avg 100/mo

        call_count = 0

        async def _execute(stmt, **kw):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [mtd_row]
            else:
                result.all.return_value = [hist_row]
            return result

        svc.db.execute = _execute
        result = await svc._check_spending_anomaly(_account_ids())
        assert result is not None
        assert result.priority == "medium"

    async def test_picks_worst_merchant_across_multiple(self):
        """When two merchants both anomalous, picks the one with higher ratio."""
        svc = _svc()

        # Merchant A: avg 100/mo, mtd 300 → ratio 3x
        # Merchant B: avg 100/mo, mtd 500 → ratio 5x → worst
        mtd_a = _row("Gym", 300.0)
        mtd_b = _row("Casino", 500.0)
        hist_a = _row("Gym", 300.0)   # avg 100/mo
        hist_b = _row("Casino", 300.0)  # avg 100/mo

        call_count = 0

        async def _execute(stmt, **kw):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [mtd_a, mtd_b]
            else:
                result.all.return_value = [hist_a, hist_b]
            return result

        svc.db.execute = _execute
        result = await svc._check_spending_anomaly(_account_ids())
        assert result is not None
        assert "Casino" in result.title

    async def test_skips_merchants_with_negligible_history(self):
        """Merchant with hist_avg < $5/mo is skipped (new merchant)."""
        svc = _svc()

        mtd_row = _row("NewPlace", 200.0)
        hist_row = _row("NewPlace", 9.0)  # avg 3/mo < $5 threshold

        call_count = 0

        async def _execute(stmt, **kw):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [mtd_row]
            else:
                result.all.return_value = [hist_row]
            return result

        svc.db.execute = _execute
        result = await svc._check_spending_anomaly(_account_ids())
        assert result is None

    async def test_amount_is_excess_over_average(self):
        """insight.amount should be mtd - avg."""
        svc = _svc()

        # avg 100/mo, mtd 300 → excess 200
        mtd_row = _row("Store", 300.0)
        hist_row = _row("Store", 300.0)  # avg 100/mo

        call_count = 0

        async def _execute(stmt, **kw):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all.return_value = [mtd_row]
            else:
                result.all.return_value = [hist_row]
            return result

        svc.db.execute = _execute
        result = await svc._check_spending_anomaly(_account_ids())
        assert result is not None
        assert result.amount == pytest.approx(200.0, abs=0.01)


# ── TestCheckBudgetOverrun ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCheckBudgetOverrun:
    async def test_returns_none_when_no_account_ids(self):
        svc = _svc()
        result = await svc._check_budget_overrun(uuid.uuid4(), None, [])
        assert result is None

    async def test_returns_none_early_in_month(self):
        """days_elapsed < 3 (day 1 or 2) → return None without DB hit."""
        svc = _svc()
        # Mock today as day 2
        with patch(
            "app.services.smart_insights_service.date"
        ) as mock_date:
            mock_date.today.return_value = date(2025, 6, 2)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = await svc._check_budget_overrun(
                uuid.uuid4(), None, _account_ids()
            )
        assert result is None

    async def test_returns_none_when_no_budgets(self):
        svc = _svc()
        # First execute (budgets) returns empty
        result_mock = MagicMock()
        result_mock.all.return_value = []
        svc.db.execute = AsyncMock(return_value=result_mock)

        result = await svc._check_budget_overrun(
            uuid.uuid4(), None, _account_ids()
        )
        assert result is None

    async def test_returns_none_when_on_track(self):
        """Projected spend within budget limit → no insight."""
        svc = _svc()

        budget = _budget_row("Groceries", 500.0)
        # Simulate: 15 days elapsed, $200 MTD → projected = (200/15)*30 = 400 < 500
        with patch(
            "app.services.smart_insights_service.date"
        ) as mock_date:
            mock_date.today.return_value = date(2025, 6, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

            call_count = 0

            async def _execute(stmt, **kw):
                nonlocal call_count
                call_count += 1
                res = MagicMock()
                if call_count == 1:
                    res.all.return_value = [budget]
                else:
                    res.scalar.return_value = 200.0
                return res

            svc.db.execute = _execute
            result = await svc._check_budget_overrun(
                uuid.uuid4(), None, _account_ids()
            )
        assert result is None

    async def test_fires_when_projected_exceeds_threshold(self):
        """Projected spend >= budget * 1.05 → fires insight."""
        svc = _svc()

        budget = _budget_row("Dining", 300.0)
        # 10 days elapsed, $200 MTD → projected = (200/10)*30 = 600 >> 300*1.05=315
        with patch(
            "app.services.smart_insights_service.date"
        ) as mock_date:
            mock_date.today.return_value = date(2025, 6, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

            call_count = 0

            async def _execute(stmt, **kw):
                nonlocal call_count
                call_count += 1
                res = MagicMock()
                if call_count == 1:
                    res.all.return_value = [budget]
                else:
                    res.scalar.return_value = 200.0
                return res

            svc.db.execute = _execute
            result = await svc._check_budget_overrun(
                uuid.uuid4(), None, _account_ids()
            )
        assert result is not None
        assert result.type == INSIGHT_BUDGET_OVERRUN
        assert "Dining" in result.title
        assert result.category == "spending"

    async def test_priority_high_when_overrun_exceeds_20pct(self):
        """Overrun > 20% of budget limit → high priority."""
        svc = _svc()

        budget = _budget_row("Entertainment", 200.0)
        # 10 days, $200 MTD → projected $600; overrun $400 > 20% of $200
        with patch(
            "app.services.smart_insights_service.date"
        ) as mock_date:
            mock_date.today.return_value = date(2025, 6, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

            call_count = 0

            async def _execute(stmt, **kw):
                nonlocal call_count
                call_count += 1
                res = MagicMock()
                if call_count == 1:
                    res.all.return_value = [budget]
                else:
                    res.scalar.return_value = 200.0
                return res

            svc.db.execute = _execute
            result = await svc._check_budget_overrun(
                uuid.uuid4(), None, _account_ids()
            )
        assert result is not None
        assert result.priority == "high"

    async def test_priority_medium_when_overrun_at_10pct(self):
        """Overrun ≤ 20% of budget → medium priority."""
        svc = _svc()

        # Budget $1000; 15 days, MTD $540 → projected = (540/15)*30 = 1080
        # overrun = 80; 80/1000 = 8% ≤ 20% → medium
        budget = _budget_row("Groceries", 1000.0)
        with patch(
            "app.services.smart_insights_service.date"
        ) as mock_date:
            mock_date.today.return_value = date(2025, 6, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

            call_count = 0

            async def _execute(stmt, **kw):
                nonlocal call_count
                call_count += 1
                res = MagicMock()
                if call_count == 1:
                    res.all.return_value = [budget]
                else:
                    res.scalar.return_value = 540.0
                return res

            svc.db.execute = _execute
            result = await svc._check_budget_overrun(
                uuid.uuid4(), None, _account_ids()
            )
        assert result is not None
        assert result.priority == "medium"

    async def test_picks_worst_budget_across_multiple(self):
        """When multiple budgets overrun, picks the one with highest projected spend."""
        svc = _svc()

        b1 = _budget_row("Dining", 200.0)
        b2 = _budget_row("Travel", 500.0)

        # 10 days elapsed
        # b1: MTD $100 → projected $300, overrun $100
        # b2: MTD $400 → projected $1200, overrun $700 → worst
        with patch(
            "app.services.smart_insights_service.date"
        ) as mock_date:
            mock_date.today.return_value = date(2025, 6, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

            call_count = 0

            async def _execute(stmt, **kw):
                nonlocal call_count
                call_count += 1
                res = MagicMock()
                if call_count == 1:
                    # budgets query
                    res.all.return_value = [b1, b2]
                elif call_count == 2:
                    res.scalar.return_value = 100.0  # b1 MTD
                else:
                    res.scalar.return_value = 400.0  # b2 MTD
                return res

            svc.db.execute = _execute
            result = await svc._check_budget_overrun(
                uuid.uuid4(), None, _account_ids()
            )
        assert result is not None
        assert "Travel" in result.title

    async def test_amount_is_projected_overrun(self):
        """insight.amount should be projected - limit."""
        svc = _svc()

        budget = _budget_row("Dining", 300.0)
        # 10 days, $200 MTD → projected $600, overrun $300
        with patch(
            "app.services.smart_insights_service.date"
        ) as mock_date:
            mock_date.today.return_value = date(2025, 6, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

            call_count = 0

            async def _execute(stmt, **kw):
                nonlocal call_count
                call_count += 1
                res = MagicMock()
                if call_count == 1:
                    res.all.return_value = [budget]
                else:
                    res.scalar.return_value = 200.0
                return res

            svc.db.execute = _execute
            result = await svc._check_budget_overrun(
                uuid.uuid4(), None, _account_ids()
            )
        assert result is not None
        assert result.amount == pytest.approx(300.0, abs=0.01)

    async def test_returns_none_when_mtd_spend_is_zero(self):
        """No spend yet → skip budget (can't project from zero)."""
        svc = _svc()

        budget = _budget_row("Groceries", 400.0)
        with patch(
            "app.services.smart_insights_service.date"
        ) as mock_date:
            mock_date.today.return_value = date(2025, 6, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

            call_count = 0

            async def _execute(stmt, **kw):
                nonlocal call_count
                call_count += 1
                res = MagicMock()
                if call_count == 1:
                    res.all.return_value = [budget]
                else:
                    res.scalar.return_value = 0.0
                return res

            svc.db.execute = _execute
            result = await svc._check_budget_overrun(
                uuid.uuid4(), None, _account_ids()
            )
        assert result is None
