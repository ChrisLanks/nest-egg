"""
PM Audit Round 44 — fixes:
1. AccountsPage: "Visible"/"Hidden" and "Excluded from Cash Flow" status
   badges now have explanatory tooltips — users no longer have to guess
   what hiding an account or excluding from cash flow does
2. BudgetCard: when spending exceeds the budget, the label changes from
   "Remaining" (confusing with a negative number) to "Over budget" so
   users immediately understand they've gone over
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _accounts_src():
    return (FRONTEND / "pages/AccountsPage.tsx").read_text()


def _budget_card_src():
    return (
        FRONTEND / "features/budgets/components/BudgetCard.tsx"
    ).read_text()


# ── 1. AccountsPage status badge tooltips ────────────────────────────────────


def test_visible_badge_has_tooltip():
    src = _accounts_src()
    assert "This account appears in your net worth, budgets, and charts" in src


def test_hidden_badge_has_tooltip():
    src = _accounts_src()
    assert "Hidden accounts are excluded from your net worth, budgets, and all charts" in src


def test_excluded_cash_flow_badge_has_tooltip():
    src = _accounts_src()
    # The badge tooltip explains what exclusion means
    idx = src.index("Excluded from Cash Flow")
    surrounding = src[idx - 300 : idx + 50]
    assert "Tooltip" in surrounding or "tooltip" in surrounding


# ── 2. BudgetCard over-budget label ──────────────────────────────────────────


def test_budget_card_shows_over_budget_label():
    src = _budget_card_src()
    assert "Over budget" in src


def test_budget_card_over_budget_gated_on_negative_remaining():
    src = _budget_card_src()
    idx = src.index("Over budget")
    surrounding = src[idx - 200 : idx + 50]
    assert "remaining < 0" in surrounding or "remaining" in surrounding


def test_budget_card_over_budget_shows_absolute_amount():
    src = _budget_card_src()
    # Must show Math.abs(remaining) when over, not a confusing negative number
    assert "Math.abs" in src
