"""
PM Audit Round 58 — fixes:
1. HouseholdSettingsPage first-invite modal: "Your Household Is Growing!" fires
   immediately when an invitation is *sent*, not when it's accepted — creating
   false expectations. Changed to "Invitation Sent!" (factually accurate) and
   "We sent an invitation to..." (vs. the self-congratulatory "You just sent").

2. HouseholdSettingsPage modal feature bullet: "Control data visibility with
   granular permissions" is developer-speak. Changed to plain English:
   "Choose what each person can see and edit."

3. GettingStartedWidget step CTA: "→ Do it now" is weak and informal. A user
   reading a task list doesn't know what "do it" refers to. Changed to
   "Open →" — concise and clear.

4. AccountsPage permission toasts: "No accounts to modify — you do not have
   permission to modify these accounts" is passive and leaves the user stuck.
   Changed to "No changes made — these accounts belong to another household
   member. Only they can modify them." — explains WHY and points to the owner.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _household_src():
    return (FRONTEND / "pages/HouseholdSettingsPage.tsx").read_text()


def _widget_src():
    return (
        FRONTEND
        / "features/dashboard/widgets/GettingStartedWidget.tsx"
    ).read_text()


def _accounts_src():
    return (FRONTEND / "pages/AccountsPage.tsx").read_text()


# ── 1. Invitation modal heading ───────────────────────────────────────────────


def test_invite_modal_no_household_growing():
    src = _household_src()
    assert "Your Household Is Growing" not in src


def test_invite_modal_uses_invitation_sent():
    src = _household_src()
    assert "Invitation Sent!" in src


def test_invite_modal_no_you_just_sent():
    src = _household_src()
    assert "You just sent your first invitation" not in src


# ── 2. Feature bullet: no "granular permissions" jargon ───────────────────────


def test_modal_no_granular_permissions():
    src = _household_src()
    assert "granular permissions" not in src


def test_modal_plain_english_permissions():
    src = _household_src()
    assert "Choose what each person can see and edit" in src


# ── 3. GettingStartedWidget CTA ───────────────────────────────────────────────


def test_widget_no_do_it_now():
    src = _widget_src()
    assert "Do it now" not in src


def test_widget_uses_open_cta():
    src = _widget_src()
    assert "Open →" in src


# ── 4. AccountsPage permission toasts ────────────────────────────────────────


def test_accounts_no_no_accounts_to_modify():
    src = _accounts_src()
    assert "No accounts to modify" not in src


def test_accounts_no_do_not_have_permission():
    src = _accounts_src()
    assert "You do not have permission to modify these accounts" not in src


def test_accounts_permission_toast_explains_owner():
    src = _accounts_src()
    assert "belong to another household member" in src
