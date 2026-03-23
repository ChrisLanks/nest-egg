"""
PM Audit Round 42 — fixes:
1. AccountsPage cash-flow toggle tooltip: now explains WHY you'd exclude an
   account (prevent double-counting), not just WHAT it does
2. AccountsPage bulk delete dialog: now lists specific account names being
   deleted so users know exactly what they're about to lose
3. HouseholdSettingsPage guest role: help text is now dynamic — shows
   a plain-English description of Viewer vs Advisor that clarifies capabilities
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _accounts_src():
    return (FRONTEND / "pages/AccountsPage.tsx").read_text()


def _household_src():
    return (FRONTEND / "pages/HouseholdSettingsPage.tsx").read_text()


# ── 1. Cash-flow tooltip explains WHY to use it ──────────────────────────────


def test_cash_flow_tooltip_explains_double_counting():
    src = _accounts_src()
    assert "double-counting" in src


def test_cash_flow_exclude_tooltip_mentions_mortgage_example():
    src = _accounts_src()
    assert "mortgage" in src.lower()


# ── 2. Bulk delete dialog lists account names ────────────────────────────────


def test_delete_dialog_shows_account_names():
    src = _accounts_src()
    # The dialog should map selected account IDs to names
    assert "accounts?.find((a) => a.id === id)?.name" in src


def test_delete_dialog_mentions_associated_data():
    src = _accounts_src()
    idx = src.index("This action cannot be undone")
    surrounding = src[idx - 200 : idx + 50]
    assert "transactions" in surrounding or "holdings" in surrounding


# ── 3. HouseholdSettingsPage role help text is dynamic ───────────────────────


def test_household_viewer_help_text_is_specific():
    src = _household_src()
    assert "Viewers can see balances, transactions, and budgets" in src


def test_household_advisor_help_text_is_specific():
    src = _household_src()
    assert "Advisors can view everything and also add or edit" in src


def test_household_role_help_text_is_dynamic():
    src = _household_src()
    idx = src.index("Viewers can see balances")
    surrounding = src[idx - 100 : idx + 50]
    assert "guestRole" in surrounding
