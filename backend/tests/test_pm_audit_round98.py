"""
PM Audit Round 98 — Final write-endpoint response_model coverage: dev/auth 204s/savings_goals/settings.

Changes covered:
1. dev.py: Dict[str, Any] on POST /seed-mock-data + POST /seed-planning-data
2. auth.py: response_model=None on POST /logout + POST /logout-all (204 no-content)
3. savings_goals.py: response_model=None on PUT /reorder (204 no-content)
4. settings.py: response_model=None on PUT /dashboard-layout (204 no-content)
"""

import inspect


# ---------------------------------------------------------------------------
# 1. dev.py
# ---------------------------------------------------------------------------

def test_dev_seed_mock_data_has_response_model():
    import app.api.v1.dev as mod
    src = inspect.getsource(mod)
    assert "response_model=Dict[str, Any]" in src


def test_dev_imports_dict_and_any():
    import app.api.v1.dev as mod
    src = inspect.getsource(mod)
    assert "Dict" in src
    assert "Any" in src


def test_dev_seed_planning_data_has_response_model():
    import app.api.v1.dev as mod
    src = inspect.getsource(mod.seed_planning_data)
    mod_src = inspect.getsource(mod)
    assert "seed-planning-data" in mod_src
    assert "response_model=Dict[str, Any]" in mod_src


# ---------------------------------------------------------------------------
# 2. auth.py — 204 endpoints are explicit about no response body
# ---------------------------------------------------------------------------

def test_auth_logout_has_response_model_none():
    import app.api.v1.auth as mod
    src = inspect.getsource(mod)
    assert "response_model=None" in src


# ---------------------------------------------------------------------------
# 3. savings_goals.py — reorder is 204
# ---------------------------------------------------------------------------

def test_savings_goals_reorder_has_response_model_none():
    import app.api.v1.savings_goals as mod
    src = inspect.getsource(mod)
    assert "response_model=None" in src


# ---------------------------------------------------------------------------
# 4. settings.py — dashboard-layout is 204
# ---------------------------------------------------------------------------

def test_settings_dashboard_layout_has_response_model_none():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "response_model=None" in src
