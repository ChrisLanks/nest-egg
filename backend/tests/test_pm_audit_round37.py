"""
PM Audit Round 37 — fixes:
1. WelcomePage: Continue button on step 0 is disabled until a goal is selected
2. WelcomePage: Dashboard style cards have "Start here" / "Experienced investors"
   recommendation badges
3. WelcomePage: Dashboard step subtitle is goal-aware (mentions relevant widgets)
4. WelcomePage: Advanced features checkbox removed from step 0; replaced with a
   post-onboarding toast for investments/retirement users
5. GoalContextBanner: spending goal + no accounts now redirects to /accounts
   instead of /budgets (same pattern as investments goal)
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _banner_src():
    return (FRONTEND / "features/dashboard/GoalContextBanner.tsx").read_text()


# ── 1. Continue disabled until goal selected ─────────────────────────────────


def test_continue_disabled_without_goal():
    src = _welcome_src()
    assert "isDisabled={step === 0 && !selectedGoal}" in src


# ── 2. Recommended badges on dashboard cards ─────────────────────────────────


def test_dashboard_cards_have_start_here_badge():
    src = _welcome_src()
    assert "Start here" in src


def test_dashboard_cards_have_experienced_badge():
    src = _welcome_src()
    assert "Experienced investors" in src


def test_start_here_badge_on_simple_card():
    src = _welcome_src()
    idx = src.index("Start here")
    surrounding = src[idx - 200 : idx + 50]
    assert '"simple"' in surrounding or "simple" in surrounding


def test_experienced_badge_on_advanced_card():
    src = _welcome_src()
    idx = src.index("Experienced investors")
    surrounding = src[idx - 200 : idx + 50]
    assert '"advanced"' in surrounding or "advanced" in surrounding


# ── 3. Goal-aware dashboard step subtitle ────────────────────────────────────


def test_dashboard_step_mentions_retirement_widgets():
    src = _welcome_src()
    assert "retirement planner" in src


def test_dashboard_step_mentions_investment_widgets():
    src = _welcome_src()
    assert "portfolio overview" in src


def test_dashboard_step_mentions_spending_widgets():
    src = _welcome_src()
    assert "budgets and spending" in src


# ── 4. Advanced checkbox removed, toast added ────────────────────────────────


def test_advanced_checkbox_removed():
    src = _welcome_src()
    # The checkbox opt-in on step 0 must be gone
    assert "I\u2019m an experienced investor \u2014 show advanced features" not in src
    assert "showAdvancedNav" not in src


def test_advanced_toast_added_for_investments_retirement():
    src = _welcome_src()
    # A toast hints about advanced features for investments/retirement goal users
    assert "Advanced features available" in src


def test_advanced_toast_conditioned_on_goal():
    src = _welcome_src()
    idx = src.index("Advanced features available")
    surrounding = src[idx - 200 : idx + 50]
    assert "investments" in surrounding or "retirement" in surrounding


# ── 5. Spending + no-accounts banner redirects to /accounts ──────────────────


def test_banner_spending_no_accounts_config_exists():
    src = _banner_src()
    assert "SPENDING_NO_ACCOUNTS_CONFIG" in src


def test_banner_spending_no_accounts_path_is_accounts():
    src = _banner_src()
    idx = src.index("SPENDING_NO_ACCOUNTS_CONFIG")
    surrounding = src[idx : idx + 200]
    assert '"/accounts"' in surrounding


def test_banner_accounts_query_enabled_for_spending():
    src = _banner_src()
    assert 'goal === "spending"' in src


def test_banner_spending_config_used_when_no_accounts():
    src = _banner_src()
    # The config selection logic must check for spending goal
    assert 'goal === "spending"' in src
    assert "SPENDING_NO_ACCOUNTS_CONFIG" in src
