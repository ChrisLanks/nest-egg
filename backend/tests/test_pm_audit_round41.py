"""
PM Audit Round 41 — fixes:
1. WelcomePage step 4 (Ready): spending + no account linked → primary CTA
   changes to "Connect an Account" → /accounts (not "Set my first budget"
   → /budgets, which would show an empty page with no transactions)
2. DashboardPage GettingStartedEmptyState: spending subtext no longer
   promises "2 minutes" — replaced with accurate description that explains
   transactions import after an account is connected
3. SavingsGoalsPage: spending goal now has a tailored empty state description
   (was falling through to generic copy)
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _dashboard_src():
    return (FRONTEND / "pages/DashboardPage.tsx").read_text()


def _savings_src():
    return (FRONTEND / "pages/SavingsGoalsPage.tsx").read_text()


# ── 1. WelcomePage step 4 CTA redirects to accounts when no account linked ───


def test_step4_primary_cta_is_connect_account_when_no_account():
    src = _welcome_src()
    assert "Connect an Account" in src


def test_step4_cta_redirects_to_accounts_path():
    src = _welcome_src()
    idx = src.index("Connect an Account")
    surrounding = src[idx - 300 : idx + 300]
    assert '"/accounts"' in surrounding or "'/accounts'" in surrounding


def test_step4_cta_gated_on_spending_and_no_account_linked():
    src = _welcome_src()
    idx = src.index("Connect an Account")
    surrounding = src[idx - 300 : idx + 50]
    assert "spending" in surrounding
    assert "accountLinked" in surrounding


# ── 2. DashboardPage spending subtext removed "2 minutes" promise ─────────────


def test_dashboard_spending_subtext_no_longer_says_two_minutes():
    src = _dashboard_src()
    # Old copy that overpromises without an account
    assert "In about 2 minutes" not in src


def test_dashboard_spending_subtext_mentions_account_connection():
    src = _dashboard_src()
    assert "Connect an account and your transactions import automatically" in src


# ── 3. SavingsGoalsPage has spending goal copy ────────────────────────────────


def test_savings_goals_has_spending_goal_copy():
    src = _savings_src()
    assert "You said you want to track spending" in src


def test_savings_goals_spending_copy_mentions_savings_goal():
    src = _savings_src()
    idx = src.index("You said you want to track spending")
    surrounding = src[idx : idx + 150]
    assert "savings goal" in surrounding
