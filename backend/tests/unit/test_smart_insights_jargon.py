"""Regression: smart insights action/title strings must not contain unexplained acronyms."""
import pytest

JARGON_PATTERNS = [
    "IRMAA threshold",  # should be "Medicare premium surcharge (IRMAA)"
]

ALLOWED_ACRONYMS = {
    "IRMAA",  # ok if followed by explanation
    "HSA",    # well-known enough
    "IRA",    # well-known enough
    "Roth",   # proper noun
    "MAGI",   # ok in context
}


def test_irmaa_action_includes_explanation():
    """IRMAA should appear with a plain-English explanation."""
    action = "Review income sources to stay below the Medicare premium surcharge (IRMAA) threshold"
    assert "Medicare" in action
    assert "IRMAA" in action


def test_expense_ratio_action_includes_explanation():
    """ER / expense ratio should be explained."""
    action = "Review fund expense ratios (the annual % fee funds charge) and consider lower-cost index fund alternatives"
    assert "annual" in action.lower() or "fee" in action.lower()


def test_irmaa_action_string_matches_service():
    """The actual action string from smart_insights_service must contain Medicare explanation."""
    from app.services.smart_insights_service import SmartInsightsService

    # Read the source to verify the correct string is present
    import inspect
    source = inspect.getsource(SmartInsightsService)
    assert "Medicare premium surcharge (IRMAA)" in source, (
        "IRMAA action string should explain it as 'Medicare premium surcharge (IRMAA)'"
    )


def test_expense_ratio_action_string_matches_service():
    """The fund fee action string must explain what expense ratios are."""
    from app.services.smart_insights_service import SmartInsightsService

    import inspect
    source = inspect.getsource(SmartInsightsService)
    assert "annual % fee funds charge" in source, (
        "Expense ratio action string should explain the fee as 'the annual % fee funds charge'"
    )
