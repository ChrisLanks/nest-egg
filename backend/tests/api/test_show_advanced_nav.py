"""Tests for show_advanced_nav cross-device persistence."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.user import User


def _auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.api
class TestShowAdvancedNav:
    """show_advanced_nav defaults, GET profile, PATCH profile, and /auth/me."""

    def test_new_user_defaults_to_false(self, client: TestClient, test_user: User):
        """show_advanced_nav should default to False for a newly created user."""
        response = client.get(
            "/api/v1/settings/profile",
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 200
        assert response.json()["show_advanced_nav"] is False

    def test_patch_sets_true(self, client: TestClient, test_user: User):
        """PATCH /settings/profile with show_advanced_nav=true persists the value."""
        response = client.patch(
            "/api/v1/settings/profile",
            json={"show_advanced_nav": True},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 200
        assert response.json()["show_advanced_nav"] is True

    def test_get_profile_returns_updated_value(self, client: TestClient, test_user: User):
        """GET /settings/profile after PATCH reflects the persisted value."""
        client.patch(
            "/api/v1/settings/profile",
            json={"show_advanced_nav": True},
            headers=_auth_headers(test_user),
        )
        response = client.get(
            "/api/v1/settings/profile",
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 200
        assert response.json()["show_advanced_nav"] is True

    def test_patch_sets_false_again(self, client: TestClient, test_user: User):
        """PATCH back to false correctly resets the preference."""
        client.patch(
            "/api/v1/settings/profile",
            json={"show_advanced_nav": True},
            headers=_auth_headers(test_user),
        )
        response = client.patch(
            "/api/v1/settings/profile",
            json={"show_advanced_nav": False},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 200
        assert response.json()["show_advanced_nav"] is False

    def test_auth_me_returns_show_advanced_nav(self, client: TestClient, test_user: User):
        """/auth/me should include show_advanced_nav so the frontend can seed localStorage."""
        client.patch(
            "/api/v1/settings/profile",
            json={"show_advanced_nav": True},
            headers=_auth_headers(test_user),
        )
        response = client.get(
            "/api/v1/auth/me",
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 200
        assert "show_advanced_nav" in response.json()
        assert response.json()["show_advanced_nav"] is True

    def test_patch_without_show_advanced_nav_leaves_value_unchanged(
        self, client: TestClient, test_user: User
    ):
        """Omitting show_advanced_nav from PATCH body leaves it untouched."""
        client.patch(
            "/api/v1/settings/profile",
            json={"show_advanced_nav": True},
            headers=_auth_headers(test_user),
        )
        # PATCH something unrelated
        client.patch(
            "/api/v1/settings/profile",
            json={"display_name": "Test"},
            headers=_auth_headers(test_user),
        )
        response = client.get(
            "/api/v1/settings/profile",
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 200
        assert response.json()["show_advanced_nav"] is True
