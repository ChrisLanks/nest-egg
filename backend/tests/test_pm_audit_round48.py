"""
PM Audit Round 48 — fixes:
1. "Sidebar" copy errors: three user-facing strings incorrectly told users to find
   the Accounts page "in the sidebar" — but the app has a top navigation bar, not
   a sidebar. Fixed to reference the Accounts page by name or top navigation.
   - DashboardPage: "Accounts page in the top navigation"
   - WelcomePage: "from the Accounts page"
   - InvestmentsPage: "from the Accounts page"
2. SS Optimizer column headers used "die 78 / die 85 / die 92" language — morbid
   and nonstandard. Changed to "to 78 / to 85 / to 92" which is the convention
   used by financial planning tools (ssa.gov, AARP, etc.).
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _dashboard_src():
    return (FRONTEND / "pages/DashboardPage.tsx").read_text()


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _investments_src():
    return (FRONTEND / "pages/InvestmentsPage.tsx").read_text()


def _ss_src():
    return (FRONTEND / "pages/SSClaimingPage.tsx").read_text()


# ── 1. No stale "sidebar" references in user-facing copy ─────────────────────


def test_dashboard_no_sidebar_reference():
    src = _dashboard_src()
    # The empty state help text used to say "from the Accounts page in the sidebar"
    assert "in the sidebar" not in src


def test_welcome_no_sidebar_reference():
    src = _welcome_src()
    # Post-connection success message must not reference a sidebar
    idx = src.index("You can add more accounts")
    surrounding = src[idx : idx + 100]
    assert "sidebar" not in surrounding


def test_investments_no_sidebar_reference():
    src = _investments_src()
    # The investments empty-state hint must not reference a sidebar
    idx = src.index("You can also add accounts")
    surrounding = src[idx : idx + 100]
    assert "sidebar" not in surrounding


def test_dashboard_references_top_nav_or_accounts_page():
    src = _dashboard_src()
    # Replacement must point users to the right place
    assert "top navigation" in src or "Accounts page" in src


def test_welcome_references_accounts_page():
    src = _welcome_src()
    idx = src.index("You can add more accounts")
    surrounding = src[idx : idx + 100]
    assert "Accounts page" in surrounding


def test_investments_references_accounts_page():
    src = _investments_src()
    idx = src.index("You can also add accounts")
    surrounding = src[idx : idx + 100]
    assert "Accounts page" in surrounding


# ── 2. SS Optimizer: professional longevity scenario column labels ────────────


def test_ss_no_die_language():
    src = _ss_src()
    assert "die 78" not in src
    assert "die 85" not in src
    assert "die 92" not in src


def test_ss_uses_to_age_language():
    src = _ss_src()
    assert "to 78" in src
    assert "to 85" in src
    assert "to 92" in src
