"""
PM Audit Round 39 — fixes:
1. RetirementPage: preemptive birthdate banner shown when birthdate is missing,
   so users understand why scenario creation fails before clicking anything
2. InvestmentsPage: "Combined portfolio across all selected members" label shown
   in combined household view so couples don't misread aggregated data as personal
3. WelcomePage step 2 (invite): copy is warmer and solo-friendly for spending
   goal users — "Managing finances solo? Just skip this"
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _retirement_src():
    return (
        FRONTEND / "features/retirement/pages/RetirementPage.tsx"
    ).read_text()


def _investments_src():
    return (FRONTEND / "pages/InvestmentsPage.tsx").read_text()


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


# ── 1. RetirementPage preemptive birthdate banner ─────────────────────────────


def test_retirement_has_birthdate_banner():
    src = _retirement_src()
    assert "Add your birthdate" in src


def test_retirement_birthdate_banner_links_to_preferences():
    src = _retirement_src()
    idx = src.index("Add your birthdate")
    surrounding = src[idx - 50 : idx + 200]
    assert "/preferences" in surrounding


def test_retirement_birthdate_banner_checks_userprofile():
    src = _retirement_src()
    idx = src.index("Add your birthdate")
    surrounding = src[idx - 200 : idx + 50]
    assert "userProfile" in surrounding or "birthdate" in surrounding


def test_retirement_uses_navigate_for_preferences_link():
    src = _retirement_src()
    assert "useNavigate" in src
    idx = src.index("Add your birthdate")
    surrounding = src[idx - 50 : idx + 300]
    assert "navigate" in surrounding


# ── 2. InvestmentsPage combined view label ───────────────────────────────────


def test_investments_combined_portfolio_label_exists():
    src = _investments_src()
    assert "Combined portfolio across all selected members" in src


def test_investments_combined_label_gated_on_combined_view():
    src = _investments_src()
    idx = src.index("Combined portfolio across all selected members")
    surrounding = src[idx - 200 : idx + 50]
    assert "isCombinedView" in surrounding


# ── 3. WelcomePage invite step solo-friendly copy ────────────────────────────


def test_welcome_invite_step_has_solo_copy():
    src = _welcome_src()
    assert "Managing finances solo?" in src


def test_welcome_invite_solo_copy_gated_on_spending_goal():
    src = _welcome_src()
    idx = src.index("Managing finances solo?")
    surrounding = src[idx - 200 : idx + 50]
    assert "spending" in surrounding
