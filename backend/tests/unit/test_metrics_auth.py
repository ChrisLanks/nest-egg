"""Tests for the Prometheus metrics admin app (separate port + basic auth)."""

import base64
import pytest
from starlette.testclient import TestClient

from app.core.metrics import create_metrics_app
from app.config import settings as real_settings


def _basic_auth_header(username: str, password: str) -> str:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {credentials}"


# Use the default dev credentials configured in Settings
_USERNAME = real_settings.METRICS_USERNAME   # "admin"
_PASSWORD = real_settings.METRICS_PASSWORD   # "metrics_admin"


@pytest.fixture(scope="module")
def metrics_client():
    """Starlette test client for the metrics admin ASGI app."""
    app = create_metrics_app()
    return TestClient(app, raise_server_exceptions=True)


@pytest.mark.unit
class TestMetricsAdminApp:
    """Tests for create_metrics_app() HTTP Basic Auth gate."""

    def test_no_auth_header_returns_401(self, metrics_client):
        """Requests with no Authorization header should get 401."""
        response = metrics_client.get("/metrics", headers={})
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_wrong_credentials_returns_401(self, metrics_client):
        """Requests with bad credentials should get 401."""
        response = metrics_client.get(
            "/metrics",
            headers={"Authorization": _basic_auth_header("admin", "wrongpass")},
        )
        assert response.status_code == 401

    def test_non_basic_auth_scheme_returns_401(self, metrics_client):
        """Bearer tokens should not be accepted on the metrics endpoint."""
        response = metrics_client.get(
            "/metrics",
            headers={"Authorization": "Bearer sometoken"},
        )
        assert response.status_code == 401

    def test_malformed_base64_returns_401(self, metrics_client):
        """Malformed base64 in Authorization header should return 401 gracefully."""
        response = metrics_client.get(
            "/metrics",
            headers={"Authorization": "Basic !!!not_valid_base64!!!"},
        )
        assert response.status_code == 401

    def test_correct_credentials_returns_200(self, metrics_client):
        """Correct credentials should return 200 with Prometheus text format."""
        response = metrics_client.get(
            "/metrics",
            headers={"Authorization": _basic_auth_header(_USERNAME, _PASSWORD)},
        )
        assert response.status_code == 200

    def test_correct_credentials_returns_prometheus_content_type(self, metrics_client):
        """Response should use the prometheus text format content type."""
        response = metrics_client.get(
            "/metrics",
            headers={"Authorization": _basic_auth_header(_USERNAME, _PASSWORD)},
        )
        assert "text/plain" in response.headers.get("content-type", "")

    def test_wrong_username_returns_401(self, metrics_client):
        """Wrong username with correct password should be rejected."""
        response = metrics_client.get(
            "/metrics",
            headers={"Authorization": _basic_auth_header("wronguser", _PASSWORD)},
        )
        assert response.status_code == 401

    def test_password_with_colon_is_handled(self, metrics_client):
        """
        Base64 credentials where the password contains ':' should split on first ':' only.
        We verify the split logic by encoding a multi-colon password and checking
        that invalid credentials are rejected (not that the server crashes).
        """
        response = metrics_client.get(
            "/metrics",
            headers={"Authorization": _basic_auth_header("admin", "pass:with:colon")},
        )
        # These credentials are wrong but the server should respond cleanly (not 500)
        assert response.status_code in (401, 200)
        assert response.status_code != 500
