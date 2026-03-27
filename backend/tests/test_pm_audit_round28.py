"""
PM Audit Round 28 — fixes:
1. Household benefits text is now solo-inclusive (no "both of you" language)
2. Household name label softens for any selected goal (not just spending/investments)
3. Invite step heading/description is optional-framing, not couple-centric
4. Invite form label changed from "Partner's email" to "Their email address"
5. Advanced Features hint shown in nav when showAdvancedNav is off
6. Dashboard empty state is goal-aware (retirement, investments, spending steps)
7. Retirement page empty state references onboarding goal when goal=retirement
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _layout_src():
    return (FRONTEND / "components/Layout.tsx").read_text()


def _dashboard_src():
    return (FRONTEND / "pages/DashboardPage.tsx").read_text()


def _retirement_src():
    return (
        FRONTEND / "features/retirement/pages/RetirementPage.tsx"
    ).read_text()


# ── 1. Household benefits text — no couple-only language ──────────────────────


def test_household_benefits_no_both_of_your_accounts():
    src = _welcome_src()
    assert "across both of your accounts" not in src


def test_household_benefits_no_can_both_retire():
    src = _welcome_src()
    assert "can both retire when you want" not in src


def test_household_benefits_no_one_of_you():
    src = _welcome_src()
    assert "what if one of you stops working" not in src


def test_household_benefits_inclusive_net_worth():
    src = _welcome_src()
    assert "across all connected accounts" in src


# ── 2. Household name label softens for any goal ─────────────────────────────


def test_household_name_label_softens_for_any_goal():
    src = _welcome_src()
    # The label should check selectedGoal (truthy) — not just specific goals
    assert "selectedGoal\n                  ? \"What should we call your finances?\"" in src or \
           "selectedGoal\r\n                  ? \"What should we call your finances?\"" in src or \
           "selectedGoal" in src and "What should we call your finances?" in src


def test_household_name_softer_label_text_present():
    src = _welcome_src()
    assert "What should we call your finances?" in src


# ── 3. Invite step is framed as optional ─────────────────────────────────────


def test_invite_step_heading_is_optional():
    src = _welcome_src()
    assert "Invite Someone? (Optional)" in src


def test_invite_step_says_skip_if_solo():
    src = _welcome_src()
    assert "managing finances on your own" in src


def test_invite_step_no_built_for_couples_only():
    src = _welcome_src()
    assert "Nest Egg is built for couples and families" not in src


# ── 4. Invite form label is inclusive ────────────────────────────────────────


def test_invite_form_label_not_partner():
    src = _welcome_src()
    assert "Partner's email address" not in src


def test_invite_form_label_is_their_email():
    src = _welcome_src()
    assert "Their email address" in src


# ── 5. Advanced Features hint in nav ─────────────────────────────────────────


def test_layout_shows_advanced_hint_when_nav_off():
    src = _layout_src()
    assert "!showAdvancedNav" in src
    # The hint is now a notification toast, not an inline button
    assert "Advanced features available" in src


def test_layout_advanced_hint_links_to_preferences():
    src = _layout_src()
    # The hint notification should link to /preferences
    hint_idx = src.index("Advanced features available")
    surrounding = src[hint_idx - 300 : hint_idx + 300]
    assert "/preferences" in surrounding


def test_layout_advanced_hint_has_tooltip():
    src = _layout_src()
    hint_idx = src.index("Advanced features available")
    surrounding = src[hint_idx - 500 : hint_idx + 300]
    assert "FIRE planning" in surrounding or "advanced" in surrounding.lower()


# ── 6. Dashboard empty state is goal-aware ───────────────────────────────────


def test_dashboard_has_goal_steps_for_retirement():
    src = _dashboard_src()
    assert "retirement" in src
    assert "Set your birthdate in Preferences" in src


def test_dashboard_has_goal_steps_for_investments():
    src = _dashboard_src()
    assert "Connect your investment account" in src


def test_dashboard_passes_goal_to_empty_state():
    src = _dashboard_src()
    assert "goal={onboardingGoal}" in src


def test_dashboard_reads_goal_from_localstorage():
    src = _dashboard_src()
    assert 'nest-egg-onboarding-goal' in src


def test_dashboard_button_label_changes_for_investments_goal():
    src = _dashboard_src()
    assert "Connect an Investment Account" in src


# ── 7. Retirement empty state references onboarding goal ─────────────────────


def test_retirement_empty_state_references_goal_key():
    src = _retirement_src()
    assert "nest-egg-onboarding-goal" in src


def test_retirement_empty_state_has_goal_aware_text():
    src = _retirement_src()
    assert "You said you want to plan for retirement" in src
