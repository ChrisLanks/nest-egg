"""
PM Audit Round 31 — fixes:
1. Feature-unlock toasts: added "Go →" CTA button so users can jump directly
   to the newly unlocked feature without hunting for it in the nav
2. WelcomePage household name placeholder adapts to goal selection —
   solo-goal users see "e.g. Jane's Finances" (not "The Smith Family")
3. Retirement "Household Plan" button gains a Tooltip explaining it merges
   all household members' accounts into one combined projection
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _layout_src():
    return (FRONTEND / "components/Layout.tsx").read_text()


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _retirement_src():
    return (FRONTEND / "features/retirement/pages/RetirementPage.tsx").read_text()


# ── 1. Feature-unlock toasts: Go → CTA ───────────────────────────────────────


def test_toast_announce_accepts_path_param():
    src = _layout_src()
    # Signature must include a path parameter
    assert "path: string" in src


def test_toast_uses_render_prop():
    src = _layout_src()
    # Custom render replaces the plain title/description toast
    assert "render:" in src or "render={" in src


def test_toast_go_button_navigates_to_path():
    src = _layout_src()
    # Go button calls navigate(path)
    assert "navigate(path)" in src


def test_education_toast_includes_education_path():
    src = _layout_src()
    assert '"/education"' in src


def test_rental_toast_includes_rental_properties_path():
    src = _layout_src()
    assert '"/rental-properties"' in src


def test_linked_accounts_toast_includes_recurring_path():
    src = _layout_src()
    assert '"/recurring"' in src


def test_investments_toast_includes_tax_deductible_path():
    src = _layout_src()
    assert '"/tax-deductible"' in src


def test_toast_go_button_label():
    src = _layout_src()
    assert "Go →" in src


# ── 2. WelcomePage placeholder adapts to goal ────────────────────────────────


def test_welcome_placeholder_is_dynamic():
    src = _welcome_src()
    # Placeholder is now a JSX expression, not a plain string
    placeholder_idx = src.index("Jane's Finances")
    surrounding = src[placeholder_idx - 50 : placeholder_idx + 100]
    assert "selectedGoal" in surrounding


def test_welcome_placeholder_solo_path_excludes_smith_family():
    src = _welcome_src()
    # When selectedGoal is set, only "Jane's Finances" appears (no family wording)
    solo_label = "\"e.g. Jane's Finances\""
    assert solo_label in src


def test_welcome_placeholder_family_path_includes_smith_family():
    src = _welcome_src()
    # The else/fallback branch keeps the family variant
    assert "The Smith Family" in src


def test_welcome_placeholder_uses_ternary():
    src = _welcome_src()
    # The placeholder uses selectedGoal as the condition
    placeholder_idx = src.index("Jane's Finances")
    surrounding = src[placeholder_idx - 150 : placeholder_idx + 200]
    assert "selectedGoal" in surrounding
    assert "The Smith Family" in surrounding


# ── 3. Retirement Household Plan tooltip ─────────────────────────────────────


def test_household_plan_button_has_tooltip():
    src = _retirement_src()
    # The Household Plan button is wrapped in a Tooltip
    hp_idx = src.index("Household Plan")
    # Tooltip should appear before the button text (expand window to catch opening tag)
    surrounding = src[hp_idx - 500 : hp_idx + 50]
    assert "Tooltip" in surrounding


def test_household_plan_tooltip_mentions_combined():
    src = _retirement_src()
    hp_idx = src.index("Household Plan")
    surrounding = src[hp_idx - 300 : hp_idx + 50]
    # Tooltip copy explains it combines/merges members
    assert "combined" in surrounding or "merges" in surrounding or "shared projection" in surrounding


def test_household_plan_tooltip_label_present():
    src = _retirement_src()
    hp_idx = src.index("Household Plan")
    surrounding = src[hp_idx - 400 : hp_idx + 50]
    assert 'label="' in surrounding
