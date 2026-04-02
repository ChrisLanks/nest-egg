"""Tests for GET /retirement/salary-estimate."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.user import User


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.mark.api
class TestSalaryEstimate:
    def test_returns_none_when_no_transactions(self, client: TestClient, test_user: User):
        """With no income transactions, estimated_annual_salary should be None."""
        response = client.get(
            "/api/v1/retirement/salary-estimate",
            headers=_auth(test_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estimated_annual_salary"] is None
        assert data["source"] == "none"

    def test_response_has_required_fields(self, client: TestClient, test_user: User):
        """Response always includes estimated_annual_salary, source, and note."""
        response = client.get(
            "/api/v1/retirement/salary-estimate",
            headers=_auth(test_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "estimated_annual_salary" in data
        assert "source" in data
        assert "note" in data

    def test_requires_authentication(self, client: TestClient):
        """Unauthenticated request should return 401/403."""
        response = client.get("/api/v1/retirement/salary-estimate")
        assert response.status_code in (401, 403)

    def test_user_id_param_accepted(self, client: TestClient, test_user: User):
        """Passing user_id query param should not 422 (even if no data)."""
        response = client.get(
            f"/api/v1/retirement/salary-estimate?user_id={test_user.id}",
            headers=_auth(test_user),
        )
        assert response.status_code == 200

    def test_invalid_user_id_returns_200_not_500(self, client: TestClient, test_user: User):
        """An invalid UUID in user_id should be ignored gracefully, not 500."""
        response = client.get(
            "/api/v1/retirement/salary-estimate?user_id=not-a-uuid",
            headers=_auth(test_user),
        )
        assert response.status_code == 200
