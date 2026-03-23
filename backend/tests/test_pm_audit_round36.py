"""
PM Audit Round 36 — fixes:
1. AcceptInvitationPage: removed React.FC type annotation (React not imported)
   — replaced with plain arrow function which is idiomatic React 18+
2. InvestmentsPage: empty state now goal-aware — investments-goal users see
   "Let's look at your investments" and a personalised description that
   acknowledges their stated goal, mirroring the pattern on other pages
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _accept_src():
    return (FRONTEND / "pages/AcceptInvitationPage.tsx").read_text()


def _investments_src():
    return (FRONTEND / "pages/InvestmentsPage.tsx").read_text()


# ── 1. AcceptInvitationPage: no bare React.FC reference ─────────────────────


def test_accept_page_no_react_fc():
    src = _accept_src()
    # React.FC used without importing React — was a TS error
    assert "React.FC" not in src


def test_accept_page_is_plain_arrow_function():
    src = _accept_src()
    # Component is now a plain arrow function
    assert "AcceptInvitationPage = () => {" in src


# ── 2. InvestmentsPage goal-aware empty state ────────────────────────────────


def test_investments_imports_auth_store():
    src = _investments_src()
    assert "useAuthStore" in src


def test_investments_reads_onboarding_goal():
    src = _investments_src()
    assert "onboardingGoal" in src
    assert "nest-egg-onboarding-goal" in src


def test_investments_empty_state_goal_aware_heading():
    src = _investments_src()
    assert "Let's look at your investments" in src


def test_investments_empty_state_investments_condition():
    src = _investments_src()
    heading_idx = src.index("Let's look at your investments")
    surrounding = src[heading_idx - 100 : heading_idx + 50]
    assert 'onboardingGoal === "investments"' in surrounding


def test_investments_empty_state_personalized_description():
    src = _investments_src()
    assert "You said you want to understand your investments" in src


def test_investments_empty_state_fallback_still_present():
    src = _investments_src()
    assert "No investment accounts yet" in src
