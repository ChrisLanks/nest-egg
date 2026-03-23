"""
PM Audit Round 45 — fix:
The "+ Advanced" button in the top navigation header was visually out of place
and cluttered the nav. Removed it entirely. Advanced features discovery is now
handled by the existing feature-discovery toast system — a one-time notification
fires when the user has accounts but hasn't enabled advanced features yet,
pointing them to Preferences → Display.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _layout_src():
    return (FRONTEND / "components/Layout.tsx").read_text()


# ── Removed: "+ Advanced" button from nav header ─────────────────────────────


def test_advanced_button_removed_from_nav():
    src = _layout_src()
    # The old nav button with "+ Advanced" text must be gone
    assert "+ Advanced" not in src


def test_no_tooltip_wrapping_advanced_nav_button():
    src = _layout_src()
    # The tooltip+button combo that sat in the nav bar must be gone
    assert "FIRE planning, Tax Projection and more are hidden. Enable Advanced Features" not in src


# ── Added: one-time discovery toast for advanced features ─────────────────────


def test_advanced_nav_hint_toast_added():
    src = _layout_src()
    assert "advanced-nav-hint" in src


def test_advanced_nav_hint_fires_when_not_enabled():
    src = _layout_src()
    idx = src.index("advanced-nav-hint")
    surrounding = src[idx - 200 : idx + 50]
    assert "showAdvancedNav" in surrounding


def test_advanced_nav_hint_only_fires_when_user_has_accounts():
    src = _layout_src()
    idx = src.index("advanced-nav-hint")
    surrounding = src[idx - 200 : idx + 50]
    # Should be gated on having at least one account type
    assert (
        "hasInvestments" in surrounding
        or "hasLinkedAccounts" in surrounding
        or "has529" in surrounding
        or "hasRental" in surrounding
    )


def test_advanced_nav_hint_links_to_preferences():
    src = _layout_src()
    idx = src.index("advanced-nav-hint")
    surrounding = src[idx : idx + 200]
    assert "/preferences" in surrounding
