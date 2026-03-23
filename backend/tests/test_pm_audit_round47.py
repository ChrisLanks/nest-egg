"""
PM Audit Round 47 — fixes:
1. First-login view notification: on login_count === 1, a one-time toast fires
   telling the user which view they're in (Combined / personal / other member)
   and where to change settings (Preferences → Display).
2. Tab-unlock notifications: every conditional nav item that becomes visible
   automatically (not by manual toggle) now fires a one-time toast when it
   first unlocks:
   - Rental Properties (rental property account added)
   - Mortgage Planner (mortgage account added)
   - Debt Payoff (loan/credit card added)
   - SS Optimizer (user's age reaches 50+)
   Previously only Education, Rental, Linked Accounts, and Investments were
   announced; Mortgage, Debt Payoff, and SS Optimizer were silent.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _layout_src():
    return (FRONTEND / "components/Layout.tsx").read_text()


# ── 1. First-login view notification ─────────────────────────────────────────


def test_first_login_toast_fires_on_login_count_1():
    src = _layout_src()
    assert "nest-egg-first-login-view-shown" in src


def test_first_login_toast_gated_on_login_count():
    src = _layout_src()
    idx = src.index("nest-egg-first-login-view-shown")
    surrounding = src[idx - 200 : idx + 50]
    assert "login_count" in surrounding


def test_first_login_toast_mentions_view():
    src = _layout_src()
    assert "You're viewing data in" in src


def test_first_login_toast_shows_combined_view_label():
    src = _layout_src()
    assert "Combined (all household members)" in src


def test_first_login_toast_links_to_preferences():
    src = _layout_src()
    idx = src.index("nest-egg-first-login-view-shown")
    surrounding = src[idx : idx + 1400]
    assert "/preferences" in surrounding


def test_first_login_toast_mentions_view_switcher():
    src = _layout_src()
    assert "view switcher" in src


# ── 2. Mortgage nav unlock notification ──────────────────────────────────────


def test_mortgage_nav_announce_key_exists():
    src = _layout_src()
    assert '"mortgage-nav"' in src


def test_mortgage_nav_announcement_gated_on_has_mortgage():
    src = _layout_src()
    idx = src.index('"mortgage-nav"')
    surrounding = src[idx - 100 : idx + 50]
    assert "hasMortgage" in surrounding


def test_mortgage_nav_links_to_mortgage_path():
    src = _layout_src()
    idx = src.index('"mortgage-nav"')
    surrounding = src[idx : idx + 200]
    assert '"/mortgage"' in surrounding


# ── 3. Debt Payoff nav unlock notification ────────────────────────────────────


def test_debt_payoff_announce_key_exists():
    src = _layout_src()
    assert '"debt-payoff-nav"' in src


def test_debt_payoff_gated_on_has_debt():
    src = _layout_src()
    idx = src.index('"debt-payoff-nav"')
    surrounding = src[idx - 100 : idx + 50]
    assert "hasDebt" in surrounding


def test_debt_payoff_links_to_debt_payoff_path():
    src = _layout_src()
    idx = src.index('"debt-payoff-nav"')
    surrounding = src[idx : idx + 200]
    assert '"/debt-payoff"' in surrounding


# ── 4. SS Optimizer nav unlock notification ───────────────────────────────────


def test_ss_optimizer_announce_key_exists():
    src = _layout_src()
    assert '"ss-optimizer-nav"' in src


def test_ss_optimizer_gated_on_is_ss_age():
    src = _layout_src()
    idx = src.index('"ss-optimizer-nav"')
    surrounding = src[idx - 100 : idx + 50]
    assert "isSsAge" in surrounding


def test_ss_optimizer_links_to_ss_claiming_path():
    src = _layout_src()
    idx = src.index('"ss-optimizer-nav"')
    surrounding = src[idx : idx + 200]
    assert '"/ss-claiming"' in surrounding


# ── 5. All new flags derived and in dependency array ─────────────────────────


def test_has_mortgage_flag_derived():
    src = _layout_src()
    assert 'const hasMortgage' in src


def test_has_debt_flag_derived():
    src = _layout_src()
    assert 'const hasDebt' in src


def test_is_ss_age_flag_derived():
    src = _layout_src()
    assert 'const isSsAge' in src


def test_new_flags_in_effect_deps():
    src = _layout_src()
    # All three new flags must be in the useEffect dependency array
    idx = src.index('"ss-optimizer-nav"')
    dep_array = src[idx : idx + 800]
    assert "hasMortgage" in dep_array
    assert "hasDebt" in dep_array
    assert "isSsAge" in dep_array
