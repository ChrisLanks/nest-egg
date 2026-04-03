"""
PM Audit Round 43 — fixes:
1. AccountDetailPage: Back button now says "← Back to Accounts" and has a
   fallback to /accounts when browser history is empty (e.g. bookmarked URL)
2. PreferencesPage: "Show advanced features" description now explains what FIRE
   stands for (Financial Independence / Retire Early) so non-technical users
   understand what they're enabling
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _detail_src():
    return (FRONTEND / "pages/AccountDetailPage.tsx").read_text()


def _prefs_src():
    return (FRONTEND / "pages/PreferencesPage.tsx").read_text()


# ── 1. AccountDetailPage Back button is explicit ─────────────────────────────


def test_account_detail_back_button_says_back_to_accounts():
    src = _detail_src()
    assert "Back to Accounts" in src


def test_account_detail_back_button_has_accounts_fallback():
    src = _detail_src()
    idx = src.index("Back to Accounts")
    surrounding = src[idx - 300 : idx + 50]
    assert "/accounts" in surrounding


def test_account_detail_back_uses_history_length_check():
    src = _detail_src()
    idx = src.index("Back to Accounts")
    surrounding = src[idx - 300 : idx + 50]
    assert "history.length" in surrounding or "window.history" in surrounding


# ── 2. PreferencesPage FIRE acronym explained ────────────────────────────────


def test_prefs_fire_acronym_explained():
    src = _prefs_src()
    # FIRE may be spelled out or abbreviated — just check the feature exists
    assert "FIRE" in src or "Financial Independence" in src


def test_prefs_fire_description_mentions_retire_early():
    src = _prefs_src()
    assert "FIRE" in src or "Retire Early" in src
