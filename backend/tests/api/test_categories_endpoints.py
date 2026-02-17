"""Integration tests for category endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.api
class TestCategoryEndpoints:
    """Test category API endpoints."""

    def test_create_category_success(self, client: TestClient, auth_headers):
        """Test successful category creation."""
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Test Category",
                "color": "#FF0000",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Category"
        assert data["color"] == "#FF0000"
        assert data["is_custom"] is True
        assert "id" in data

    def test_create_category_with_parent(self, client: TestClient, auth_headers):
        """Test creating subcategory with parent."""
        # Create parent category first
        parent_response = client.post(
            "/api/v1/categories",
            json={"name": "Parent Category"},
            headers=auth_headers,
        )
        assert parent_response.status_code == 201
        parent_id = parent_response.json()["id"]

        # Create child category
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Child Category",
                "parent_category_id": parent_id,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Child Category"
        assert data["parent_category_id"] == parent_id

    def test_create_category_empty_name_fails(self, client: TestClient, auth_headers):
        """Test category creation with empty name fails."""
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "   ",  # Empty after stripping
                "color": "#FF0000",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "Category name cannot be empty" in response.text

    def test_create_category_too_long_fails(self, client: TestClient, auth_headers):
        """Test category creation with too long name fails."""
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "A" * 101,  # 101 characters, exceeds 100 limit
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "100 characters or less" in response.text

    def test_create_category_xss_attempt_fails(self, client: TestClient, auth_headers):
        """Test category creation with XSS attempt fails."""
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "<script>alert('xss')</script>",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "cannot contain < or >" in response.text

    def test_create_category_invalid_color_fails(self, client: TestClient, auth_headers):
        """Test category creation with invalid hex color fails."""
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Test Category",
                "color": "not-a-hex-color",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "valid hex code" in response.text

    def test_create_category_short_hex_color(self, client: TestClient, auth_headers):
        """Test category creation with short hex color (3 chars) succeeds."""
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Test Category",
                "color": "F00",  # Short hex
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["color"] == "#F00"  # Validator adds # prefix

    def test_create_category_exceeds_depth_fails(self, client: TestClient, auth_headers):
        """Test creating category with parent that already has parent fails."""
        # Create grandparent
        grandparent_response = client.post(
            "/api/v1/categories",
            json={"name": "Grandparent"},
            headers=auth_headers,
        )
        grandparent_id = grandparent_response.json()["id"]

        # Create parent (child of grandparent)
        parent_response = client.post(
            "/api/v1/categories",
            json={
                "name": "Parent",
                "parent_category_id": grandparent_id,
            },
            headers=auth_headers,
        )
        parent_id = parent_response.json()["id"]

        # Try to create child of parent (would be 3 levels deep)
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Child",
                "parent_category_id": parent_id,
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Maximum 2 levels allowed" in response.text

    def test_list_categories(self, client: TestClient, auth_headers):
        """Test listing categories."""
        # Create a test category
        client.post(
            "/api/v1/categories",
            json={"name": "Test List Category"},
            headers=auth_headers,
        )

        # List categories
        response = client.get(
            "/api/v1/categories",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least our created category
        assert any(c["name"] == "Test List Category" for c in data if c.get("is_custom"))

    def test_get_category_by_id(self, client: TestClient, auth_headers):
        """Test getting specific category by ID."""
        # Create category
        create_response = client.post(
            "/api/v1/categories",
            json={"name": "Get By ID Test"},
            headers=auth_headers,
        )
        category_id = create_response.json()["id"]

        # Get category
        response = client.get(
            f"/api/v1/categories/{category_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category_id
        assert data["name"] == "Get By ID Test"

    def test_get_category_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent category returns 404."""
        fake_id = str(uuid4())
        response = client.get(
            f"/api/v1/categories/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_update_category(self, client: TestClient, auth_headers):
        """Test updating category."""
        # Create category
        create_response = client.post(
            "/api/v1/categories",
            json={"name": "Original Name"},
            headers=auth_headers,
        )
        category_id = create_response.json()["id"]

        # Update category
        response = client.patch(
            f"/api/v1/categories/{category_id}",
            json={
                "name": "Updated Name",
                "color": "#00FF00",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["color"] == "#00FF00"

    def test_update_category_empty_name_fails(self, client: TestClient, auth_headers):
        """Test updating category with empty name fails."""
        # Create category
        create_response = client.post(
            "/api/v1/categories",
            json={"name": "Test Category"},
            headers=auth_headers,
        )
        category_id = create_response.json()["id"]

        # Try to update with empty name
        response = client.patch(
            f"/api/v1/categories/{category_id}",
            json={"name": "   "},  # Empty after stripping
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
        assert "Category name cannot be empty" in response.text

    def test_delete_category(self, client: TestClient, auth_headers):
        """Test deleting category."""
        # Create category
        create_response = client.post(
            "/api/v1/categories",
            json={"name": "Delete Me"},
            headers=auth_headers,
        )
        category_id = create_response.json()["id"]

        # Delete category
        response = client.delete(
            f"/api/v1/categories/{category_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/categories/{category_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_category_not_found(self, client: TestClient, auth_headers):
        """Test deleting non-existent category returns 404."""
        fake_id = str(uuid4())
        response = client.delete(
            f"/api/v1/categories/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_create_category_without_auth_fails(self, client: TestClient):
        """Test creating category without authentication fails."""
        response = client.post(
            "/api/v1/categories",
            json={"name": "Test Category"},
        )

        assert response.status_code == 401  # Unauthorized
