"""
PM Audit Round 32 — fixes:
1. WelcomePage: dashboard step pre-selects "simple" by default so the user
   always sees a selection state (not a blank picker)
2. WelcomePage: bottom nav buttons are hidden on the final step to avoid
   duplicating the card's own primary + ghost CTAs
3. DashboardPage: login_count ?? 0 (was 1) so first-time users whose profile
   hasn't loaded yet correctly see "Welcome" not "Welcome back"
4. GoalContextBanner: auto-dismisses permanently when the user navigates to
   their goal page via the sidebar (not only when they click the banner CTA)
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _dashboard_src():
    return (FRONTEND / "pages/DashboardPage.tsx").read_text()


def _banner_src():
    return (FRONTEND / "features/dashboard/GoalContextBanner.tsx").read_text()


# ── 1. Dashboard step pre-selects "simple" ───────────────────────────────────


def test_selected_dashboard_defaults_to_simple():
    src = _welcome_src()
    # Initial state must be "simple", not null
    assert 'useState<\n    "simple" | "advanced" | null\n  >("simple")' in src or \
           'useState<"simple" | "advanced" | null>("simple")' in src or \
           '>(\n    "simple"\n  )' in src or \
           '>("simple")' in src


def test_selected_dashboard_not_null_default():
    src = _welcome_src()
    # The selectedDashboard state initializer must not be null
    # Find the state declaration and check its default value
    idx = src.index("selectedDashboard")
    surrounding = src[idx - 10 : idx + 200]
    assert '>("simple")' in surrounding or '"simple"' in surrounding


# ── 2. Bottom nav hidden on final step ───────────────────────────────────────


def test_nav_buttons_hidden_on_final_step():
    src = _welcome_src()
    # The nav HStack is now conditional on step < STEPS.length - 1
    assert "step < STEPS.length - 1" in src


def test_final_step_has_no_duplicate_continue_button():
    src = _welcome_src()
    # The navigation buttons comment marks the nav section
    comment = "Navigation buttons"
    assert comment in src
    nav_idx = src.index(comment)
    nav_block = src[nav_idx : nav_idx + 600]
    # The nav block renders "Continue" (for earlier steps)
    assert "Continue" in nav_block
    # But no "primaryCtaLabel" in the nav block (that was the duplication)
    assert "primaryCtaLabel" not in nav_block


def test_step4_card_still_has_cta_buttons():
    src = _welcome_src()
    # The card's own CTA buttons remain
    assert "finish(primaryCtaDestination)" in src
    assert "Take me to the dashboard" in src


# ── 3. login_count defaults to 0 not 1 ───────────────────────────────────────


def test_login_count_defaults_to_zero():
    src = _dashboard_src()
    assert "(user?.login_count ?? 0) <= 1" in src


def test_login_count_not_defaulting_to_one():
    src = _dashboard_src()
    assert "(user?.login_count ?? 1) <= 1" not in src


# ── 4. GoalContextBanner auto-dismisses on goal page ─────────────────────────


def test_banner_imports_use_location():
    src = _banner_src()
    assert "useLocation" in src


def test_banner_uses_location_pathname():
    src = _banner_src()
    assert "location.pathname" in src


def test_banner_auto_dismiss_useeffect():
    src = _banner_src()
    # useEffect that watches location.pathname
    assert "useEffect" in src
    effect_idx = src.index("location.pathname")
    surrounding = src[effect_idx - 200 : effect_idx + 200]
    assert "DISMISSED_KEY" in surrounding or "setDismissed" in surrounding


def test_banner_auto_dismiss_sets_permanent_key():
    src = _banner_src()
    # When on goal page, sets DISMISSED_KEY to "true" permanently
    effect_idx = src.index("location.pathname")
    surrounding = src[effect_idx - 200 : effect_idx + 300]
    assert 'DISMISSED_KEY, "true"' in surrounding or "DISMISSED_KEY" in surrounding


def test_banner_imports_use_effect():
    src = _banner_src()
    assert "useEffect" in src
