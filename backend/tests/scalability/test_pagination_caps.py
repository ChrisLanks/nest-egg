"""Tests for pagination depth caps."""

import pytest


class TestPaginationCaps:
    """Verify OFFSET pagination is capped to prevent deep scans."""

    @pytest.mark.asyncio
    async def test_report_templates_skip_over_cap_rejected(self, authenticated_client):
        """skip > 10000 on report templates should be rejected (422)."""
        response = await authenticated_client.get(
            "/api/v1/reports/templates",
            params={"skip": 10001},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_report_templates_skip_at_cap_accepted(self, authenticated_client):
        """skip = 10000 on report templates should be accepted."""
        response = await authenticated_client.get(
            "/api/v1/reports/templates",
            params={"skip": 10000},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_permissions_audit_offset_over_cap_rejected(self, authenticated_client):
        """offset > 10000 on audit log should be rejected (422)."""
        response = await authenticated_client.get(
            "/api/v1/permissions/audit",
            params={"offset": 10001},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_permissions_audit_offset_at_cap_accepted(self, authenticated_client):
        """offset = 10000 on audit log should be accepted."""
        response = await authenticated_client.get(
            "/api/v1/permissions/audit",
            params={"offset": 10000},
        )
        assert response.status_code == 200
