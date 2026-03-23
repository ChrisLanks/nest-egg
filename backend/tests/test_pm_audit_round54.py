"""
PM Audit Round 54 — fixes:
1. SmartInsightsPage empty state: "surface personalized recommendations" used
   developer/product-jargon ("surface" as a verb). Changed to "generate".
2. TaxDeductiblePage empty state: "Tag transactions with tax labels ... Navigate
   to transactions and apply labels" mixed developer-speak ("tag", "labels",
   "Navigate"). Rewritten to plain English: categorize, tax category, Go to.
3. CategoriesPage: "(from provider)" is developer-speak for users who have no
   idea what "provider" means in this context. Changed to "(from your bank)".
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _insights_src():
    return (FRONTEND / "pages/SmartInsightsPage.tsx").read_text()


def _tax_deductible_src():
    return (FRONTEND / "pages/TaxDeductiblePage.tsx").read_text()


def _categories_src():
    return (FRONTEND / "pages/CategoriesPage.tsx").read_text()


# ── 1. SmartInsightsPage: no "surface" jargon ────────────────────────────────


def test_smart_insights_no_surface_verb():
    src = _insights_src()
    assert "surface personalized" not in src


def test_smart_insights_uses_generate():
    src = _insights_src()
    assert "generate personalized recommendations" in src


# ── 2. TaxDeductiblePage: clearer empty state ─────────────────────────────────


def test_tax_deductible_no_tag_labels_speak():
    src = _tax_deductible_src()
    assert "Tag transactions with tax labels" not in src


def test_tax_deductible_no_navigate_to_transactions():
    src = _tax_deductible_src()
    # Old instruction used developer-style "Navigate to transactions"
    assert "Navigate to transactions" not in src


def test_tax_deductible_empty_state_mentions_tax_category():
    src = _tax_deductible_src()
    assert "tax category" in src


def test_tax_deductible_empty_state_says_go_to_transactions():
    src = _tax_deductible_src()
    assert "Go to Transactions" in src


# ── 3. CategoriesPage: no "from provider" ────────────────────────────────────


def test_categories_no_from_provider():
    src = _categories_src()
    assert "(from provider)" not in src


def test_categories_uses_from_your_bank():
    src = _categories_src()
    assert "(from your bank)" in src
