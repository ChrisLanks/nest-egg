"""
PM Audit Round 38 — fixes:
1. DashboardPage: subtitle below greeting is now goal-aware
   (retirement/investments/spending each get a relevant subtitle)
2. WelcomePage step 4: bg="green.50" replaced with design token "green.subtle"
   so the checkmark circle renders correctly in dark mode
3. WelcomePage "Skip for now": now calls skipToApp() (navigate only) instead
   of finish() (which permanently marks onboarding complete) — users who skip
   on day 1 will see the wizard again next login
4. WelcomePage advanced-features toast: fires before navigate() so the
   component is still mounted when the toast is triggered
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _dashboard_src():
    return (FRONTEND / "pages/DashboardPage.tsx").read_text()


# ── 1. Goal-aware dashboard subtitle ─────────────────────────────────────────


def test_dashboard_subtitle_retirement():
    src = _dashboard_src()
    assert "Here's where your retirement stands" in src


def test_dashboard_subtitle_investments():
    src = _dashboard_src()
    assert "Here's your investment overview" in src


def test_dashboard_subtitle_spending():
    src = _dashboard_src()
    assert "Here's where your money is going" in src


def test_dashboard_subtitle_uses_onboarding_goal():
    src = _dashboard_src()
    idx = src.index("Here's where your retirement stands")
    surrounding = src[idx - 100 : idx + 50]
    assert "onboardingGoal" in surrounding


# ── 2. Dark-mode safe color on step 4 ────────────────────────────────────────


def test_step4_no_hardcoded_green50():
    src = _welcome_src()
    assert 'bg="green.50"' not in src


def test_step4_uses_green_subtle():
    src = _welcome_src()
    # Accepts semantic token bg="bg.success" (resolves to green.subtle in theme)
    assert 'bg="green.subtle"' in src or 'bg="bg.success"' in src


# ── 3. Skip for now does not complete onboarding ─────────────────────────────


def test_skip_calls_skip_to_app():
    src = _welcome_src()
    # skipToApp is the safe navigate-only function
    assert "skipToApp" in src


def test_skip_to_app_does_not_call_onboarding_complete():
    src = _welcome_src()
    idx = src.index("const skipToApp")
    fn_body = src[idx : idx + 200]
    # Must not call the API endpoint that marks onboarding done
    assert "onboarding/complete" not in fn_body
    assert "onboarding_completed" not in fn_body


def test_skip_button_calls_skip_to_app():
    src = _welcome_src()
    # The ghost button on step 0 must use skipToApp, not finish()
    assert "skipToApp" in src
    # Verify it's no longer calling finish() inline for skip
    skip_idx = src.index("Skip for now")
    surrounding = src[skip_idx - 200 : skip_idx + 50]
    assert "skipToApp" in surrounding


# ── 4. Toast fires before navigate ───────────────────────────────────────────


def test_toast_before_navigate_in_finish():
    src = _welcome_src()
    # toast() call must appear before navigate() in the finish function
    finish_idx = src.index("const finish = async")
    finish_body = src[finish_idx : finish_idx + 2000]
    # Find the "Advanced features" toast specifically (not the error toast)
    adv_toast_pos = finish_body.index("Advanced features available")
    navigate_pos = finish_body.index("navigate(destination")
    assert adv_toast_pos < navigate_pos


def test_no_settimeout_around_toast():
    src = _welcome_src()
    # The old bug: setTimeout wrapped the toast causing it to fire after unmount
    assert "setTimeout" not in src
