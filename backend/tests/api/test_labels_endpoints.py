"""Integration tests for label endpoints."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.api
class TestLabelEndpoints:
    """Test label API endpoints."""

    def test_create_label_success(self, client: TestClient, auth_headers):
        """Test successful label creation."""
        response = client.post(
            "/api/v1/labels",
            json={
                "name": "Test Label",
                "color": "#FF0000",
                "is_income": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Label"
        assert data["color"] == "#FF0000"
        assert data["is_income"] is False
        assert "id" in data

    def test_create_income_label(self, client: TestClient, auth_headers):
        """Test creating income label."""
        response = client.post(
            "/api/v1/labels",
            json={
                "name": "Bonus",
                "is_income": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Bonus"
        assert data["is_income"] is True

    def test_create_label_empty_name_fails(self, client: TestClient, auth_headers):
        """Test label creation with empty name fails."""
        response = client.post(
            "/api/v1/labels",
            json={
                "name": "   ",  # Empty after stripping
                "is_income": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "Label name cannot be empty" in response.text

    def test_create_label_too_long_fails(self, client: TestClient, auth_headers):
        """Test label creation with too long name fails."""
        response = client.post(
            "/api/v1/labels",
            json={
                "name": "A" * 101,  # 101 characters, exceeds 100 limit
                "is_income": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "100 characters or less" in response.text

    def test_create_label_xss_attempt_fails(self, client: TestClient, auth_headers):
        """Test label creation with XSS attempt fails."""
        response = client.post(
            "/api/v1/labels",
            json={
                "name": "<script>alert('xss')</script>",
                "is_income": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "cannot contain < or >" in response.text

    def test_create_label_invalid_color_fails(self, client: TestClient, auth_headers):
        """Test label creation with invalid hex color fails."""
        response = client.post(
            "/api/v1/labels",
            json={
                "name": "Test Label",
                "color": "not-a-hex-color",
                "is_income": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "valid hex code" in response.text

    def test_create_label_short_hex_color(self, client: TestClient, auth_headers):
        """Test label creation with short hex color (3 chars) succeeds."""
        response = client.post(
            "/api/v1/labels",
            json={
                "name": "Test Label",
                "color": "F00",  # Short hex
                "is_income": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["color"] == "#F00"  # Validator adds # prefix

    def test_list_labels(self, client: TestClient, auth_headers):
        """Test listing labels."""
        # Create a test label
        client.post(
            "/api/v1/labels",
            json={
                "name": "Test List Label",
                "is_income": False,
            },
            headers=auth_headers,
        )

        # List labels
        response = client.get(
            "/api/v1/labels",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least our created label
        assert any(label["name"] == "Test List Label" for label in data)

    def test_list_labels_filter_by_is_income(self, client: TestClient, auth_headers):
        """Test listing labels filtered by is_income."""
        # Create income label
        client.post(
            "/api/v1/labels",
            json={
                "name": "Income Label",
                "is_income": True,
            },
            headers=auth_headers,
        )

        # Create expense label
        client.post(
            "/api/v1/labels",
            json={
                "name": "Expense Label",
                "is_income": False,
            },
            headers=auth_headers,
        )

        # List income labels
        response = client.get(
            "/api/v1/labels?is_income=true",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # All labels should be income labels
        assert all(label["is_income"] for label in data)
        assert any(label["name"] == "Income Label" for label in data)

    def test_get_label_by_id(self, client: TestClient, auth_headers):
        """Test getting specific label by ID."""
        # Create label
        create_response = client.post(
            "/api/v1/labels",
            json={
                "name": "Get By ID Test",
                "is_income": False,
            },
            headers=auth_headers,
        )
        label_id = create_response.json()["id"]

        # Get label
        response = client.get(
            f"/api/v1/labels/{label_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == label_id
        assert data["name"] == "Get By ID Test"

    def test_get_label_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent label returns 404."""
        fake_id = str(uuid4())
        response = client.get(
            f"/api/v1/labels/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_update_label(self, client: TestClient, auth_headers):
        """Test updating label."""
        # Create label
        create_response = client.post(
            "/api/v1/labels",
            json={
                "name": "Original Name",
                "is_income": False,
            },
            headers=auth_headers,
        )
        label_id = create_response.json()["id"]

        # Update label
        response = client.patch(
            f"/api/v1/labels/{label_id}",
            json={
                "name": "Updated Name",
                "color": "#00FF00",
                "is_income": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["color"] == "#00FF00"
        assert data["is_income"] is True

    def test_update_label_empty_name_fails(self, client: TestClient, auth_headers):
        """Test updating label with empty name fails."""
        # Create label
        create_response = client.post(
            "/api/v1/labels",
            json={
                "name": "Test Label",
                "is_income": False,
            },
            headers=auth_headers,
        )
        label_id = create_response.json()["id"]

        # Try to update with empty name
        response = client.patch(
            f"/api/v1/labels/{label_id}",
            json={"name": "   "},  # Empty after stripping
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "Label name cannot be empty" in response.text

    def test_delete_label(self, client: TestClient, auth_headers):
        """Test deleting label."""
        # Create label
        create_response = client.post(
            "/api/v1/labels",
            json={
                "name": "Delete Me",
                "is_income": False,
            },
            headers=auth_headers,
        )
        label_id = create_response.json()["id"]

        # Delete label
        response = client.delete(
            f"/api/v1/labels/{label_id}",
            headers=auth_headers,
        )

        assert response.status_code in [200, 204]

        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/labels/{label_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_label_not_found(self, client: TestClient, auth_headers):
        """Test deleting non-existent label returns 404."""
        fake_id = str(uuid4())
        response = client.delete(
            f"/api/v1/labels/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_create_label_without_auth_fails(self, client: TestClient):
        """Test creating label without authentication fails."""
        response = client.post(
            "/api/v1/labels",
            json={
                "name": "Test Label",
                "is_income": False,
            },
        )

        assert response.status_code in [401, 403]  # Unauthorized (FastAPI HTTPBearer returns 403)

    @pytest_asyncio.fixture
    async def test_transaction(self, db_session, test_user, test_account):
        """Create a test transaction for label tests."""
        from uuid import uuid4
        from datetime import date
        from decimal import Decimal
        from app.models.transaction import Transaction

        txn = Transaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
            merchant_name="Test Merchant",
            deduplication_hash=str(uuid4()),
        )
        db_session.add(txn)
        await db_session.commit()
        await db_session.refresh(txn)
        return {"id": str(txn.id)}

    def test_apply_label_to_transaction(
        self, client: TestClient, auth_headers, test_account, test_transaction
    ):
        """Test applying label to transaction."""
        # Create label
        label_response = client.post(
            "/api/v1/labels",
            json={
                "name": "Test Transaction Label",
                "is_income": False,
            },
            headers=auth_headers,
        )
        label_id = label_response.json()["id"]

        # Apply label to transaction
        response = client.post(
            f"/api/v1/transactions/{test_transaction['id']}/labels/{label_id}",
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]

        # Verify label is applied
        txn_response = client.get(
            f"/api/v1/transactions/{test_transaction['id']}",
            headers=auth_headers,
        )
        assert txn_response.status_code == 200
        txn_data = txn_response.json()
        assert any(label["id"] == label_id for label in txn_data.get("labels", []))

    def test_remove_label_from_transaction(
        self, client: TestClient, auth_headers, test_account, test_transaction
    ):
        """Test removing label from transaction."""
        # Create label
        label_response = client.post(
            "/api/v1/labels",
            json={
                "name": "Test Remove Label",
                "is_income": False,
            },
            headers=auth_headers,
        )
        label_id = label_response.json()["id"]

        # Apply label
        client.post(
            f"/api/v1/transactions/{test_transaction['id']}/labels/{label_id}",
            headers=auth_headers,
        )

        # Remove label
        response = client.delete(
            f"/api/v1/transactions/{test_transaction['id']}/labels/{label_id}",
            headers=auth_headers,
        )

        assert response.status_code in [200, 204]

        # Verify label is removed
        txn_response = client.get(
            f"/api/v1/transactions/{test_transaction['id']}",
            headers=auth_headers,
        )
        txn_data = txn_response.json()
        assert not any(label["id"] == label_id for label in txn_data.get("labels", []))
