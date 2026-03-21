"""Unit tests for enrichment API endpoints."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.api.v1.enrichment import (
    EnrichmentRequest,
    enrich_holdings,
    get_enrichment_status,
)
from app.models.user import User


def _mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


@pytest.mark.unit
class TestEnrichHoldings:
    @pytest.mark.asyncio
    async def test_enrich_returns_count(self):
        mock_db = AsyncMock()
        user = _mock_user()
        request = EnrichmentRequest(force_refresh=False, limit=20)
        background_tasks = Mock()

        with patch("app.api.v1.enrichment.financial_data_service") as mock_svc:
            mock_svc.enrich_holdings_batch = AsyncMock(return_value=5)
            result = await enrich_holdings(
                request=request,
                background_tasks=background_tasks,
                db=mock_db,
                current_user=user,
            )

        assert result.enriched_count == 5
        assert "5" in result.message

    @pytest.mark.asyncio
    async def test_enrich_force_refresh(self):
        mock_db = AsyncMock()
        user = _mock_user()
        request = EnrichmentRequest(force_refresh=True, limit=10)

        with patch("app.api.v1.enrichment.financial_data_service") as mock_svc:
            mock_svc.enrich_holdings_batch = AsyncMock(return_value=0)
            await enrich_holdings(
                request=request,
                background_tasks=Mock(),
                db=mock_db,
                current_user=user,
            )

        call_kwargs = mock_svc.enrich_holdings_batch.call_args[1]
        assert call_kwargs["force_refresh"] is True
        assert call_kwargs["limit"] == 10


@pytest.mark.unit
class TestGetEnrichmentStatus:
    @pytest.mark.asyncio
    async def test_returns_status(self):
        mock_db = AsyncMock()
        user = _mock_user()

        # First execute: total count
        # Second execute: enriched count
        total_result = Mock()
        total_result.scalar.return_value = 20

        enriched_result = Mock()
        enriched_result.scalar.return_value = 15

        mock_db.execute.side_effect = [total_result, enriched_result]

        result = await get_enrichment_status(db=mock_db, current_user=user)

        assert result["total_equity_holdings"] == 20
        assert result["enriched"] == 15
        assert result["unenriched"] == 5
        assert result["percent_enriched"] == 75.0

    @pytest.mark.asyncio
    async def test_zero_holdings(self):
        mock_db = AsyncMock()
        user = _mock_user()

        total_result = Mock()
        total_result.scalar.return_value = 0

        enriched_result = Mock()
        enriched_result.scalar.return_value = 0

        mock_db.execute.side_effect = [total_result, enriched_result]

        result = await get_enrichment_status(db=mock_db, current_user=user)

        assert result["total_equity_holdings"] == 0
        assert result["percent_enriched"] == 0

    @pytest.mark.asyncio
    async def test_none_scalar_defaults_to_zero(self):
        mock_db = AsyncMock()
        user = _mock_user()

        total_result = Mock()
        total_result.scalar.return_value = None

        enriched_result = Mock()
        enriched_result.scalar.return_value = None

        mock_db.execute.side_effect = [total_result, enriched_result]

        result = await get_enrichment_status(db=mock_db, current_user=user)

        assert result["total_equity_holdings"] == 0
        assert result["enriched"] == 0
