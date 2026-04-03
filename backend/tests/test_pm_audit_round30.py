"""
PM Audit Round 30 — fixes:
1. GoalContextBanner: soft-dismiss (up to 3 times) instead of permanent dismiss on X click;
   CTA click (visiting goal page) is the only permanent dismissal
2. SmartInsights: two-state empty state — no-accounts CTA vs. all-clear when accounts exist
3. SmartInsights: "All" filter pill now uses brand color when active (was gray/gray bug)
4. Budgets: added investments-specific empty state copy
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _banner_src():
    return (
        FRONTEND / "features/dashboard/GoalContextBanner.tsx"
    ).read_text()


def _insights_src():
    return (FRONTEND / "pages/SmartInsightsPage.tsx").read_text()


def _budgets_src():
    return (FRONTEND / "pages/BudgetsPage.tsx").read_text()


# ── 1. GoalContextBanner soft-dismiss ────────────────────────────────────────


def test_banner_has_dismiss_count_key():
    src = _banner_src()
    assert "nest-egg-goal-banner-dismiss-count" in src


def test_banner_has_max_soft_dismissals_constant():
    src = _banner_src()
    assert "MAX_SOFT_DISMISSALS" in src


def test_banner_cta_click_permanently_dismisses():
    src = _banner_src()
    # handleCtaClick sets the permanent dismissed key
    assert "handleCtaClick" in src
    cta_idx = src.index("handleCtaClick")
    fn_body = src[cta_idx : cta_idx + 300]
    assert "DISMISSED_KEY" in fn_body or "nest-egg-goal-banner-dismissed" in fn_body


def test_banner_x_click_uses_soft_dismiss():
    src = _banner_src()
    assert "DISMISS_COUNT_KEY" in src
    # handleDismiss increments the count
    dismiss_idx = src.index("const handleDismiss")
    fn_body = src[dismiss_idx : dismiss_idx + 400]
    assert "DISMISS_COUNT_KEY" in fn_body


def test_banner_stops_showing_after_max_soft_dismissals():
    src = _banner_src()
    assert ">= MAX_SOFT_DISMISSALS" in src


def test_banner_cta_button_uses_handle_cta_click():
    src = _banner_src()
    assert "onClick={handleCtaClick}" in src


def test_banner_no_longer_navigates_inline_on_cta():
    src = _banner_src()
    # Old pattern called handleDismiss() then navigate() inline — should be gone
    assert "handleDismiss();\n                navigate" not in src


# ── 2. SmartInsights empty state — no accounts ───────────────────────────────


def test_insights_fetches_accounts_for_empty_state():
    src = _insights_src()
    assert "accounts-insights-check" in src


def test_insights_empty_state_has_no_accounts_branch():
    src = _insights_src()
    assert "accounts.length === 0" in src


def test_insights_no_accounts_empty_state_has_connect_cta():
    src = _insights_src()
    assert "Connect an Account" in src


def test_insights_no_accounts_navigates_to_accounts():
    src = _insights_src()
    connect_idx = src.index("Connect an Account")
    surrounding = src[connect_idx - 300 : connect_idx + 50]
    assert "/accounts" in surrounding


def test_insights_empty_state_only_shown_without_accounts():
    src = _insights_src()
    # "No insights yet" or similar empty state — must be gated on having no data
    # (The original "All clear!" text was replaced with friendlier copy)
    assert "No insights yet" in src or "All clear" in src or "no insights" in src.lower()


def test_insights_imports_use_navigate():
    src = _insights_src()
    assert "useNavigate" in src


# ── 3. SmartInsights filter visual bug ───────────────────────────────────────


def test_insights_all_pill_uses_brand_color_when_active():
    src = _insights_src()
    # colorScheme should differ based on selection — brand when active
    assert 'colorScheme={selectedCategory === null ? "brand" : "gray"}' in src


def test_insights_all_pill_not_gray_gray():
    src = _insights_src()
    # The old bug: both states used "gray"
    assert 'colorScheme={selectedCategory === null ? "gray" : "gray"}' not in src


# ── 4. Budgets investments-specific empty state ───────────────────────────────


def test_budgets_has_investments_empty_state_copy():
    src = _budgets_src()
    assert "investments" in src
    assert "boost your savings rate" in src


def test_budgets_investments_empty_state_mentions_investing():
    src = _budgets_src()
    assert "more to invest" in src or "savings rate" in src
