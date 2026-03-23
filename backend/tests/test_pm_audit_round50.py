"""
PM Audit Round 50 — fixes:
1. WelcomePage "Account Settings" copy error: the security bullet point told users
   they could disconnect accounts from "Account Settings" — but that section is
   called "Accounts" in the navigation. Fixed to say "the Accounts page".
2. WelcomePage step 4 invalid design token: the ready-screen check mark circle used
   `bg="green.subtle"` which is not a defined semantic token. Changed to `bg="bg.success"`
   to match the pattern used on lines 466 and 584 of the same file.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


# ── 1. "Account Settings" copy error ─────────────────────────────────────────


def test_welcome_disconnect_no_account_settings_copy():
    src = _welcome_src()
    # The security bullet that mentions disconnecting must not say "Account Settings"
    idx = src.index("You can disconnect")
    surrounding = src[idx : idx + 100]
    assert "Account Settings" not in surrounding


def test_welcome_disconnect_references_accounts_page():
    src = _welcome_src()
    idx = src.index("You can disconnect")
    surrounding = src[idx : idx + 100]
    assert "Accounts page" in surrounding


# ── 2. Invalid `green.subtle` design token ───────────────────────────────────


def test_welcome_no_green_subtle_token():
    src = _welcome_src()
    assert 'bg="green.subtle"' not in src
    assert "bg='green.subtle'" not in src


def test_welcome_ready_screen_uses_valid_success_token():
    src = _welcome_src()
    # The ready/all-set screen icon circle must use bg.success
    idx = src.index("all set!")
    # Look back for the surrounding box that contains the check icon
    surrounding = src[idx - 500 : idx]
    assert "bg.success" in surrounding
