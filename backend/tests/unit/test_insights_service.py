"""Unit tests for InsightsService — category trends, anomaly detection."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.insights_service import InsightsService


svc = InsightsService


class TestDetectCategoryTrends:
    """Test _detect_category_trends via generate_insights mock."""

    @pytest.mark.asyncio
    async def test_empty_account_ids_returns_empty(self):
        db = AsyncMock()
        result = await svc._detect_category_trends(db, uuid4(), [])
        assert result == []


class TestDetectAnomalies:
    @pytest.mark.asyncio
    async def test_empty_account_ids_returns_empty(self):
        db = AsyncMock()
        result = await svc._detect_anomalies(db, uuid4(), [])
        assert result == []


class TestGenerateInsights:
    @pytest.mark.asyncio
    async def test_limits_to_max_insights(self):
        """generate_insights should cap at max_insights."""
        db = AsyncMock()
        org_id = uuid4()

        # Mock both sub-methods to return many insights
        fake_trends = [
            {"type": "category_increase", "title": f"Cat {i}", "priority_score": i}
            for i in range(10)
        ]
        fake_anomalies = [
            {"type": "anomaly", "title": f"Anomaly {i}", "priority_score": i + 10}
            for i in range(5)
        ]

        with patch.object(svc, "_detect_category_trends", return_value=fake_trends):
            with patch.object(svc, "_detect_anomalies", return_value=fake_anomalies):
                result = await svc.generate_insights(db, org_id, [uuid4()], max_insights=3)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_sorted_by_priority_desc(self):
        """Higher priority_score should come first."""
        db = AsyncMock()
        org_id = uuid4()

        insights = [
            {"type": "category_increase", "title": "Low", "priority_score": 10},
            {"type": "anomaly", "title": "High", "priority_score": 90},
            {"type": "category_decrease", "title": "Mid", "priority_score": 50},
        ]

        with patch.object(svc, "_detect_category_trends", return_value=insights):
            with patch.object(svc, "_detect_anomalies", return_value=[]):
                result = await svc.generate_insights(db, org_id, [uuid4()], max_insights=10)

        scores = [r["priority_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_empty_with_no_data(self):
        db = AsyncMock()
        with patch.object(svc, "_detect_category_trends", return_value=[]):
            with patch.object(svc, "_detect_anomalies", return_value=[]):
                result = await svc.generate_insights(db, uuid4(), [uuid4()])
        assert result == []
