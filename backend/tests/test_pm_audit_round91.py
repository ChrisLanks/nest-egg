"""
PM Audit Round 91 — Typed response models for notifications/savings_goals/rental_properties;
router-level rate limit for savings_goals.

Changes covered:
1. notifications.py: MarkAllReadResponse; response_model on mark-read, dismiss, mark-all-read
2. savings_goals.py: ContributionResponse + RetirementLinkResponse models;
   router-level _rate_limit dependency replaces partial inline guards;
   response_model on contributions + add-to-retirement-plan endpoints
3. rental_properties.py: RentalFieldsResponse model; response_model on PATCH endpoint
"""

import inspect


# ---------------------------------------------------------------------------
# 1. notifications.py — response models
# ---------------------------------------------------------------------------

def test_notifications_has_mark_all_read_response():
    import app.api.v1.notifications as mod
    assert hasattr(mod, "MarkAllReadResponse")
    fields = mod.MarkAllReadResponse.model_fields
    assert "marked_read" in fields


def test_notifications_mark_read_has_response_model():
    import app.api.v1.notifications as mod
    src = inspect.getsource(mod)
    assert "response_model=NotificationResponse" in src


def test_notifications_mark_all_read_has_response_model():
    import app.api.v1.notifications as mod
    src = inspect.getsource(mod)
    assert "response_model=MarkAllReadResponse" in src


def test_notifications_mark_all_read_returns_model():
    import app.api.v1.notifications as mod
    src = inspect.getsource(mod.mark_all_notifications_read)
    assert "MarkAllReadResponse(" in src


# ---------------------------------------------------------------------------
# 2. savings_goals.py — response models + router rate limit
# ---------------------------------------------------------------------------

def test_savings_goals_has_contribution_response():
    import app.api.v1.savings_goals as mod
    assert hasattr(mod, "ContributionResponse")
    fields = mod.ContributionResponse.model_fields
    assert "goal_id" in fields
    assert "contribution_amount" in fields
    assert "current_amount" in fields


def test_savings_goals_has_retirement_link_response():
    import app.api.v1.savings_goals as mod
    assert hasattr(mod, "RetirementLinkResponse")
    fields = mod.RetirementLinkResponse.model_fields
    assert "life_event_id" in fields
    assert "goal_name" in fields
    assert "target_age" in fields


def test_savings_goals_has_router_rate_limit():
    import app.api.v1.savings_goals as mod
    src = inspect.getsource(mod)
    assert "_rate_limit" in src
    assert "dependencies=[Depends(_rate_limit)]" in src


def test_savings_goals_contributions_has_response_model():
    import app.api.v1.savings_goals as mod
    src = inspect.getsource(mod)
    assert "response_model=ContributionResponse" in src


def test_savings_goals_retirement_link_has_response_model():
    import app.api.v1.savings_goals as mod
    src = inspect.getsource(mod)
    assert "response_model=RetirementLinkResponse" in src


def test_savings_goals_contribution_returns_model():
    import app.api.v1.savings_goals as mod
    src = inspect.getsource(mod.record_contribution)
    assert "ContributionResponse(" in src


def test_savings_goals_retirement_link_returns_model():
    import app.api.v1.savings_goals as mod
    src = inspect.getsource(mod.add_goal_to_retirement_plan)
    assert "RetirementLinkResponse(" in src


# ---------------------------------------------------------------------------
# 3. rental_properties.py — RentalFieldsResponse model
# ---------------------------------------------------------------------------

def test_rental_properties_has_fields_response():
    import app.api.v1.rental_properties as mod
    assert hasattr(mod, "RentalFieldsResponse")
    fields = mod.RentalFieldsResponse.model_fields
    assert "account_id" in fields
    assert "is_rental_property" in fields
    assert "rental_monthly_income" in fields


def test_rental_properties_patch_has_response_model():
    import app.api.v1.rental_properties as mod
    src = inspect.getsource(mod)
    assert "response_model=RentalFieldsResponse" in src
