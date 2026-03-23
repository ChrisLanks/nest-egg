"""
PM Audit Round 46 — fix:
Nav visibility bug: stale localStorage overrides could show data-gated nav
items (Rental Properties, SS Optimizer) even when the underlying condition
wasn't met (no rental accounts, age < 50).

Root cause: isNavVisible() checked navOverridesState first, so a persisted
"true" override from a previous session would show the item even if the
account-based condition later became false.

Fix: conditional paths (those in conditionalDefaults) now enforce the
condition first. If the condition is not met, the item is hidden regardless
of any stored override. If the condition IS met, the user override is
respected (so users can still hide items they don't want).
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _layout_src():
    return (FRONTEND / "components/Layout.tsx").read_text()


def _nav_defaults_src():
    return (FRONTEND / "hooks/useNavDefaults.ts").read_text()


# ── isNavVisible respects conditional gates ───────────────────────────────────


def test_is_nav_visible_checks_conditional_defaults_first():
    src = _layout_src()
    # The fix: conditional paths check the condition before any override
    assert "path in conditionalDefaults" in src


def test_conditional_path_returns_false_when_condition_not_met():
    src = _layout_src()
    idx = src.index("path in conditionalDefaults")
    surrounding = src[idx : idx + 300]
    # Must return false when condition is not met
    assert "if (!conditionMet) return false" in surrounding


def test_user_override_only_applied_when_condition_met():
    src = _layout_src()
    idx = src.index("if (!conditionMet) return false")
    surrounding = src[idx : idx + 200]
    assert "navOverridesState" in surrounding


# ── SS Optimizer gated at age 50 ─────────────────────────────────────────────


def test_ss_optimizer_gated_at_age_50():
    src = _nav_defaults_src()
    assert "userAge >= 50" in src


def test_ss_claiming_in_conditional_defaults():
    src = _nav_defaults_src()
    assert '"/ss-claiming"' in src


# ── Rental Properties gated on is_rental_property ────────────────────────────


def test_rental_nav_gated_on_has_rental():
    src = _nav_defaults_src()
    assert 'is_rental_property' in src
    assert '"/rental-properties": hasRental' in src
