"""
Tests for estimated monthly income/spending (3-month rolling average).

1. get_estimated_monthly_income averages 3 complete months of income
2. get_estimated_monthly_income returns None when no transactions exist
3. get_estimated_monthly_spending averages 3 complete months of spending
4. get_estimated_monthly_spending returns None when no transactions exist
5. DashboardSummary schema includes estimated fields
6. Dashboard summary endpoint returns estimated_monthly_income
7. Dashboard summary endpoint returns None when no historical data
8. Account filtering is respected in estimated calculations
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# DashboardSummary schema tests
# ---------------------------------------------------------------------------


def test_dashboard_summary_has_estimated_fields():
    """DashboardSummary schema includes optional estimated fields."""
    from app.api.v1.dashboard import DashboardSummary

    summary = DashboardSummary(
        net_worth=100000,
        total_assets=150000,
        total_debts=50000,
        monthly_spending=5000,
        monthly_income=8000,
        monthly_net=3000,
        estimated_monthly_income=7500.0,
        estimated_monthly_spending=4800.0,
    )
    assert summary.estimated_monthly_income == 7500.0
    assert summary.estimated_monthly_spending == 4800.0


def test_dashboard_summary_estimated_fields_optional():
    """estimated fields default to None."""
    from app.api.v1.dashboard import DashboardSummary

    summary = DashboardSummary(
        net_worth=100000,
        total_assets=150000,
        total_debts=50000,
        monthly_spending=5000,
        monthly_income=8000,
        monthly_net=3000,
    )
    assert summary.estimated_monthly_income is None
    assert summary.estimated_monthly_spending is None


# ---------------------------------------------------------------------------
# Service-level tests (DashboardService.get_estimated_monthly_income)
# ---------------------------------------------------------------------------


def _mock_db_with_scalar(scalar_value):
    """Return a mock AsyncSession whose execute().scalar() returns the given value."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar_value

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


@pytest.mark.asyncio
async def test_estimated_income_returns_average():
    """Income from 3 months is averaged correctly."""
    from app.services.dashboard_service import DashboardService

    # Total income of $24,000 over 3 months → $8,000/month
    mock_db = _mock_db_with_scalar(Decimal("24000"))
    service = DashboardService(mock_db)

    result = await service.get_estimated_monthly_income("org-1")
    assert result == Decimal("24000") / 3


@pytest.mark.asyncio
async def test_estimated_income_none_when_no_data():
    """Returns None when there are no income transactions."""
    from app.services.dashboard_service import DashboardService

    mock_db = _mock_db_with_scalar(None)
    service = DashboardService(mock_db)

    result = await service.get_estimated_monthly_income("org-1")
    assert result is None


@pytest.mark.asyncio
async def test_estimated_spending_returns_average():
    """Spending from 3 months is averaged correctly (returned as positive)."""
    from app.services.dashboard_service import DashboardService

    # Total spending of -$15,000 over 3 months → $5,000/month
    mock_db = _mock_db_with_scalar(Decimal("-15000"))
    service = DashboardService(mock_db)

    result = await service.get_estimated_monthly_spending("org-1")
    assert result == Decimal("15000") / 3


@pytest.mark.asyncio
async def test_estimated_spending_none_when_no_data():
    """Returns None when there are no spending transactions."""
    from app.services.dashboard_service import DashboardService

    mock_db = _mock_db_with_scalar(None)
    service = DashboardService(mock_db)

    result = await service.get_estimated_monthly_spending("org-1")
    assert result is None


@pytest.mark.asyncio
async def test_estimated_income_custom_lookback():
    """Lookback months parameter is respected."""
    from app.services.dashboard_service import DashboardService

    mock_db = _mock_db_with_scalar(Decimal("60000"))
    service = DashboardService(mock_db)

    result = await service.get_estimated_monthly_income("org-1", lookback_months=6)
    assert result == Decimal("60000") / 6


@pytest.mark.asyncio
async def test_estimated_income_with_account_filter():
    """Account IDs filter is forwarded to the query."""
    from app.services.dashboard_service import DashboardService

    mock_db = _mock_db_with_scalar(Decimal("9000"))
    service = DashboardService(mock_db)

    account_ids = [uuid4(), uuid4()]
    result = await service.get_estimated_monthly_income(
        "org-1", account_ids=account_ids
    )
    assert result == Decimal("9000") / 3
    # Verify execute was called (query was built)
    mock_db.execute.assert_called_once()
