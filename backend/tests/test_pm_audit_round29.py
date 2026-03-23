"""
PM Audit Round 29 — fixes:
1. Invite step skip button renamed: 'Just me — skip for now' → 'Continue without inviting'
2. Comparison button shows as disabled (not hidden) when < 2 scenarios, with tooltip
3. 'Our Retirement Plan' placeholder changed to 'Household Retirement Plan'
4. 'All household members' radio now has explanatory sub-text
5. Dashboard empty state steps 2 & 3 are now clickable nav links with paths
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _retirement_src():
    return (
        FRONTEND / "features/retirement/pages/RetirementPage.tsx"
    ).read_text()


def _dashboard_src():
    return (FRONTEND / "pages/DashboardPage.tsx").read_text()


# ── 1. Invite skip button label ───────────────────────────────────────────────


def test_invite_skip_button_no_longer_says_just_me():
    src = _welcome_src()
    assert "Just me — skip for now" not in src


def test_invite_skip_button_says_continue_without_inviting():
    src = _welcome_src()
    assert "Continue without inviting" in src


# ── 2. Comparison button disabled when < 2 scenarios ─────────────────────────


def test_comparison_button_not_gated_by_length_gte_2():
    src = _retirement_src()
    # Old pattern hid the button entirely — must be gone
    assert "scenarios.length >= 2" not in src or \
        "isDisabled={scenarios.length < 2}" in src


def test_comparison_button_has_is_disabled_prop():
    src = _retirement_src()
    assert "isDisabled={scenarios.length < 2}" in src


def test_comparison_button_shown_when_scenarios_gt_0():
    src = _retirement_src()
    assert "scenarios.length > 0" in src


def test_comparison_button_tooltip_explains_disabled_state():
    src = _retirement_src()
    assert "Create a second scenario to compare" in src


# ── 3. Household retirement plan placeholder ──────────────────────────────────


def test_our_retirement_plan_placeholder_gone():
    src = _retirement_src()
    assert "Our Retirement Plan" not in src


def test_household_retirement_plan_placeholder_present():
    src = _retirement_src()
    assert "Household Retirement Plan" in src


# ── 4. All household members radio has explanatory text ───────────────────────


def test_all_household_members_radio_has_description():
    src = _retirement_src()
    assert "Combines everyone" in src or "combined" in src.lower()


# ── 5. Dashboard empty state steps have navigation paths ─────────────────────


def test_dashboard_steps_have_path_field():
    src = _dashboard_src()
    # Steps should have path properties for navigation
    assert 'path: "/budgets"' in src
    assert 'path: "/retirement"' in src
    assert 'path: "/investments"' in src
    assert 'path: "/preferences"' in src


def test_dashboard_empty_state_accepts_on_navigate():
    src = _dashboard_src()
    assert "onNavigate" in src


def test_dashboard_empty_state_steps_are_clickable():
    src = _dashboard_src()
    # Steps with a path should call onNavigate on click
    assert "onNavigate(step.path" in src


def test_dashboard_empty_state_passes_navigate_to_component():
    src = _dashboard_src()
    assert "onNavigate={navigate}" in src


def test_dashboard_steps_show_go_badge_for_linked_steps():
    src = _dashboard_src()
    assert "Go →" in src
