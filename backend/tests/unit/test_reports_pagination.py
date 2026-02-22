"""Tests for GET /reports/templates pagination."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime


@pytest.mark.unit
class TestListReportTemplatesPagination:
    """Test pagination parameters on the list_report_templates endpoint."""

    def _make_template(self):
        """Return a minimal mock ReportTemplate."""
        t = MagicMock()
        t.id = uuid4()
        t.organization_id = uuid4()
        t.name = "Test Template"
        t.description = None
        t.report_type = "spending"
        t.config = {}
        t.is_shared = False
        t.created_by_user_id = uuid4()
        t.created_at = datetime.utcnow()
        t.updated_at = datetime.utcnow()
        return t

    @pytest.mark.asyncio
    async def test_default_pagination_passes_offset_and_limit(self):
        """Default call (no skip/limit) should apply offset=0, limit=50 to the query."""
        from app.api.v1.reports import list_report_templates

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.organization_id = uuid4()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.v1.reports.select") as mock_select:
            mock_query = MagicMock()
            mock_select.return_value = mock_query
            mock_query.where.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query

            await list_report_templates(
                skip=0,
                limit=50,
                current_user=mock_user,
                db=mock_db,
            )

            mock_query.offset.assert_called_once_with(0)
            mock_query.limit.assert_called_once_with(50)

    @pytest.mark.asyncio
    async def test_custom_pagination_values(self):
        """skip=10, limit=20 should be forwarded to the query."""
        from app.api.v1.reports import list_report_templates

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.organization_id = uuid4()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.v1.reports.select") as mock_select:
            mock_query = MagicMock()
            mock_select.return_value = mock_query
            mock_query.where.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query

            await list_report_templates(
                skip=10,
                limit=20,
                current_user=mock_user,
                db=mock_db,
            )

            mock_query.offset.assert_called_once_with(10)
            mock_query.limit.assert_called_once_with(20)

    @pytest.mark.asyncio
    async def test_returns_templates_as_response_objects(self):
        """Returned list should contain ReportTemplateResponse dicts."""
        from app.api.v1.reports import list_report_templates

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.organization_id = uuid4()

        template = self._make_template()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [template]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.v1.reports.select") as mock_select:
            mock_query = MagicMock()
            mock_select.return_value = mock_query
            mock_query.where.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query

            result = await list_report_templates(
                skip=0,
                limit=50,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result) == 1
        assert str(template.id) == result[0].id

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self):
        """When the query returns no rows, an empty list should be returned."""
        from app.api.v1.reports import list_report_templates

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.organization_id = uuid4()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.v1.reports.select") as mock_select:
            mock_query = MagicMock()
            mock_select.return_value = mock_query
            mock_query.where.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query

            result = await list_report_templates(
                skip=0,
                limit=50,
                current_user=mock_user,
                db=mock_db,
            )

        assert result == []
