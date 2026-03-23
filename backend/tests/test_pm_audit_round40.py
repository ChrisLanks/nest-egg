"""
PM Audit Round 40 — fixes:
1. WelcomePage step 1 (Accounts): skip note now warns spending-goal users that
   budgets require a connected account
2. WelcomePage step 4 (Ready): spending goal + no account linked shows
   "Connect a bank account first" instead of the normal 2-minute budget promise
3. BudgetsPage empty state: when spending goal + no accounts, copy now says
   "Connect a bank account first" instead of asking to pick a category (which
   requires transactions to be useful)
4. IncomeExpensesPage empty state: "No transactions" now includes a link to
   /accounts so new users know where to go
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


def _budgets_src():
    return (FRONTEND / "pages/BudgetsPage.tsx").read_text()


def _income_src():
    return (
        FRONTEND / "features/income-expenses/pages/IncomeExpensesPage.tsx"
    ).read_text()


# ── 1. WelcomePage step 1 skip note warns spending users ─────────────────────


def test_step1_skip_note_warns_spending_goal():
    src = _welcome_src()
    assert "budgets and spending tracking require at least one connected account" in src


def test_step1_skip_note_gated_on_spending_goal():
    src = _welcome_src()
    idx = src.index("budgets and spending tracking require at least one connected account")
    surrounding = src[idx - 200 : idx + 50]
    assert "spending" in surrounding


# ── 2. WelcomePage step 4 ready copy is account-aware ────────────────────────


def test_step4_no_account_shows_connect_first():
    src = _welcome_src()
    assert "Connect a bank account first" in src


def test_step4_no_account_copy_gated_on_spending_and_no_account_linked():
    src = _welcome_src()
    idx = src.index("Connect a bank account first")
    surrounding = src[idx - 200 : idx + 50]
    assert "spending" in surrounding
    assert "accountLinked" in surrounding


# ── 3. BudgetsPage empty state when no accounts ──────────────────────────────


def test_budgets_no_accounts_copy():
    src = _budgets_src()
    assert "Connect a bank account first — budgets are most useful" in src


def test_budgets_no_accounts_gated_on_has_no_accounts():
    src = _budgets_src()
    idx = src.index("Connect a bank account first — budgets are most useful")
    surrounding = src[idx - 200 : idx + 50]
    assert "hasNoAccounts" in surrounding


def test_budgets_page_queries_accounts_for_spending_goal():
    src = _budgets_src()
    assert "budgets-page-accounts" in src


# ── 4. IncomeExpensesPage empty state links to accounts ──────────────────────


def test_income_empty_state_links_to_accounts():
    src = _income_src()
    idx = src.index("No transactions found for the selected date range")
    surrounding = src[idx : idx + 400]
    assert "/accounts" in surrounding


def test_income_empty_state_uses_navigate():
    src = _income_src()
    assert "useNavigate" in src
    idx = src.index("No transactions found for the selected date range")
    surrounding = src[idx : idx + 400]
    assert "navigate" in surrounding
