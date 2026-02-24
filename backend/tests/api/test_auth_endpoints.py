"""Integration tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
@pytest.mark.auth
class TestAuthEndpoints:
    """Test authentication API endpoints."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "Xk9#mP2$vL7!qR4wZ",
                "first_name": "New",
                "last_name": "User",
                "display_name": "New User",
                "organization_name": "Test Org",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@example.com"
        assert "id" in data["user"]
        assert "hashed_password" not in data  # Should not expose password

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration with duplicate email returns same response (anti-enumeration)."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "Xk9#mP2$vL7!qR4wZ",
                "first_name": "New",
                "last_name": "User",
                "display_name": "New User",
                "organization_name": "Test Org",
            },
        )

        # Returns 201 with a generic message to prevent user enumeration
        assert response.status_code == 201
        assert "message" in response.json()

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password fails."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "weak",
                "first_name": "New",
                "last_name": "User",
                "display_name": "New User",
                "organization_name": "Test Org",
            },
        )

        assert response.status_code == 422

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "Password123!",
            },
        )

        assert response.status_code == 401

    def test_get_current_user_authenticated(self, client: TestClient, auth_headers):
        """Test getting current user with valid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "id" in data

    def test_get_current_user_unauthenticated(self, client: TestClient):
        """Test getting current user without token fails."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code in (401, 403)

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token fails."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401

    def test_refresh_token_success(self, client: TestClient, test_user):
        """Test token refresh with valid refresh token."""
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client: TestClient):
        """Test token refresh with invalid refresh token fails."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.refresh.token"},
        )

        assert response.status_code == 401
