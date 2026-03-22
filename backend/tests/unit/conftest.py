"""Shared fixtures for unit tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_http_request():
    """A minimal FastAPI Request mock for unit tests that call endpoint functions directly."""
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = {}
    return req


@pytest.fixture(autouse=True)
def patch_rate_limit(monkeypatch):
    """Auto-patch rate_limit_service.check_rate_limit to a no-op in all unit tests.

    Unit tests call endpoint functions directly, bypassing FastAPI's DI.
    Rate limiting is an infrastructure concern tested separately — patching it
    here keeps unit tests focused on endpoint logic.
    """
    async def _noop(*args, **kwargs):
        pass

    # Patch at the module level for each router that imports rate_limit_service
    for module in (
        "app.api.v1.categories",
        "app.api.v1.labels",
        "app.api.v1.savings_goals",
        "app.api.v1.transaction_splits",
    ):
        try:
            import importlib
            mod = importlib.import_module(module)
            if hasattr(mod, "rate_limit_service"):
                monkeypatch.setattr(mod.rate_limit_service, "check_rate_limit", _noop)
        except ImportError:
            pass
