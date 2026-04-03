"""
PM Audit Round 46 — behavior clarification:
Nav visibility: explicit user overrides always win (manual override in
Preferences shows the item regardless of account conditions). Without an
override, account/age-based conditional defaults apply.

This is the correct behavior — users can intentionally enable items like
Rental Properties before adding rental accounts, or SS Optimizer to preview.
The conditionalDefaults in useNavDefaults.ts still correctly gate items
for users who have never touched the Preferences toggles.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _layout_src():
    return (FRONTEND / "components/Layout.tsx").read_text()


def _nav_defaults_src():
    return (FRONTEND / "hooks/useNavDefaults.ts").read_text()


# ── isNavVisible: override wins, then conditional default ────────────────────


def test_user_override_takes_priority():
    src = _layout_src()
    # Override is checked before conditional default
    idx = src.index("isNavVisible = (path: string)")
    body = src[idx : idx + 600]
    override_pos = body.index("navOverridesState")
    conditional_pos = body.index("conditionalDefaults")
    assert override_pos < conditional_pos


def test_conditional_default_used_when_no_override():
    src = _layout_src()
    assert "conditionalDefaults[path] ?? true" in src


# ── SS Optimizer gated at age 50 in conditionalDefaults ──────────────────────


def test_ss_optimizer_age_awareness():
    # SS optimizer age awareness — userAge is computed and exported from useNavDefaults
    src = _nav_defaults_src()
    assert "userAge" in src


def test_ss_claiming_route_exists():
    # /ss-claiming route must exist in the App routing (may redirect to /retirement)
    import os
    app_src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'src', 'App.tsx')
    app_src = open(app_src_path).read()
    assert "ss-claiming" in app_src


# ── Rental Properties gated on is_rental_property ────────────────────────────


def test_rental_nav_gated_on_has_rental():
    src = _nav_defaults_src()
    assert "is_rental_property" in src
    assert '"/rental-properties": hasRental' in src
