"""
PM Audit Round 35 — fixes:
1. DashboardPage: accounts loading state is now tracked (accountsLoading) so
   the widget grid is NOT rendered while accounts are still fetching — prevents
   the flash of dashboard widgets before the getting-started empty state appears
   for new users with no accounts
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _dashboard_src():
    return (FRONTEND / "pages/DashboardPage.tsx").read_text()


# ── 1. Grid suppressed while accounts are loading ────────────────────────────


def test_accounts_loading_is_destructured():
    src = _dashboard_src()
    # isLoading must be extracted from the accounts query
    assert "isLoading: accountsLoading" in src


def test_empty_state_gated_on_not_loading():
    src = _dashboard_src()
    # Empty state condition must include !accountsLoading
    assert "!accountsLoading" in src
    # Find the JSX usage (not the component definition) by looking for onConnectBank prop
    empty_state_usage_idx = src.index("onConnectBank={onAddAccountOpen}")
    surrounding = src[empty_state_usage_idx - 200 : empty_state_usage_idx + 50]
    assert "accountsLoading" in surrounding


def test_grid_not_shown_while_loading():
    src = _dashboard_src()
    # Find the DashboardGrid JSX usage (has layout prop)
    grid_usage_idx = src.index("layout={layout}")
    surrounding = src[grid_usage_idx - 200 : grid_usage_idx + 50]
    # The condition must reference accountsLoading so it doesn't render during load
    assert "accountsLoading" in surrounding


def test_grid_not_shown_on_undefined_accounts():
    src = _dashboard_src()
    # Old bug: accounts === undefined (loading) triggered grid render
    # New: condition excludes the undefined/loading case
    grid_idx = src.index("DashboardGrid")
    surrounding = src[grid_idx - 200 : grid_idx + 20]
    # accounts === undefined alone must not be the trigger anymore
    assert "accounts === undefined" not in surrounding
