"""Tests for pagination depth caps."""

import pytest


class TestPaginationCaps:
    """Verify pagination parameters are validated."""

    @pytest.mark.asyncio
    async def test_report_templates_uses_keyset_pagination(self, authenticated_client):
        """Report templates should accept 'after' cursor, not 'skip'."""
        # skip param is now ignored (not an error, just not used)
        response = await authenticated_client.get(
            "/api/v1/reports/templates",
            params={"skip": 10001},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_report_templates_invalid_cursor_rejected(self, authenticated_client):
        """Invalid cursor format should be rejected (400)."""
        response = await authenticated_client.get(
            "/api/v1/reports/templates",
            params={"after": "not-a-valid-datetime"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_report_templates_valid_cursor_accepted(self, authenticated_client):
        """Valid ISO datetime cursor should be accepted."""
        response = await authenticated_client.get(
            "/api/v1/reports/templates",
            params={"after": "2024-01-01T00:00:00"},
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
