"""Integration tests for budget endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.api
class TestBudgetEndpoints:
    """Test budget API endpoints."""

    def test_create_budget_success(self, client: TestClient, auth_headers):
        """Test successful budget creation."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "name": "Groceries",
                "category": "Food & Dining",
                "amount": 500.00,
                "period": "MONTHLY",
                "alert_threshold": 0.80,
                "is_active": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Groceries"
        assert data["amount"] == 500.00
        assert data["period"] == "MONTHLY"
        assert "id" in data

    def test_create_budget_invalid_threshold(self, client: TestClient, auth_headers):
        """Test budget creation with invalid threshold fails."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "name": "Test",
                "category": "Shopping",
                "amount": 500.00,
                "period": "MONTHLY",
                "alert_threshold": 1.5,  # Invalid (must be 0-1)
                "is_active": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_list_budgets(self, client: TestClient, auth_headers):
        """Test listing budgets."""
        # Create a budget first
        client.post(
            "/api/v1/budgets",
            json={
                "name": "Test Budget",
                "category": "Shopping",
                "amount": 300.00,
                "period": "MONTHLY",
                "is_active": True,
            },
            headers=auth_headers,
        )

        # List budgets
        response = client.get(
            "/api/v1/budgets",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(b["name"] == "Test Budget" for b in data)

    def test_get_budget_by_id(self, client: TestClient, auth_headers):
        """Test getting specific budget by ID."""
        # Create budget
        create_response = client.post(
            "/api/v1/budgets",
            json={
                "name": "Travel",
                "category": "Travel",
                "amount": 1000.00,
                "period": "QUARTERLY",
                "is_active": True,
            },
            headers=auth_headers,
        )
        budget_id = create_response.json()["id"]

        # Get budget
        response = client.get(
            f"/api/v1/budgets/{budget_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == budget_id
        assert data["name"] == "Travel"

    def test_update_budget(self, client: TestClient, auth_headers):
        """Test updating budget."""
        # Create budget
        create_response = client.post(
            "/api/v1/budgets",
            json={
                "name": "Entertainment",
                "category": "Entertainment",
                "amount": 200.00,
                "period": "MONTHLY",
                "is_active": True,
            },
            headers=auth_headers,
        )
        budget_id = create_response.json()["id"]

        # Update budget
        response = client.patch(
            f"/api/v1/budgets/{budget_id}",
            json={
                "amount": 250.00,  # Increase budget
                "alert_threshold": 0.90,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == 250.00
        assert data["alert_threshold"] == 0.90

    def test_delete_budget(self, client: TestClient, auth_headers):
        """Test deleting budget."""
        # Create budget
        create_response = client.post(
            "/api/v1/budgets",
            json={
                "name": "Temp Budget",
                "category": "Other",
                "amount": 100.00,
                "period": "MONTHLY",
                "is_active": True,
            },
            headers=auth_headers,
        )
        budget_id = create_response.json()["id"]

        # Delete budget
        response = client.delete(
            f"/api/v1/budgets/{budget_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/api/v1/budgets/{budget_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_get_budget_unauthenticated(self, client: TestClient):
        """Test getting budget without authentication fails."""
        response = client.get("/api/v1/budgets")

        assert response.status_code == 401

    def test_create_budget_negative_amount(self, client: TestClient, auth_headers):
        """Test creating budget with negative amount fails."""
        response = client.post(
            "/api/v1/budgets",
            json={
                "name": "Invalid",
                "category": "Shopping",
                "amount": -100.00,  # Negative amount
                "period": "MONTHLY",
                "is_active": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_budget_progress_calculation(self, client: TestClient, auth_headers):
        """Test budget progress endpoint."""
        # Create budget
        create_response = client.post(
            "/api/v1/budgets",
            json={
                "name": "Dining Out",
                "category": "Food & Dining",
                "amount": 400.00,
                "period": "MONTHLY",
                "is_active": True,
            },
            headers=auth_headers,
        )
        budget_id = create_response.json()["id"]

        # Get progress (will be 0% with no transactions)
        response = client.get(
            f"/api/v1/budgets/{budget_id}/progress",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "percentage" in data
        assert "spent" in data
        assert "budget" in data
        assert "remaining" in data
