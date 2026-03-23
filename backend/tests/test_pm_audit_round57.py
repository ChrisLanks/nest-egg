"""
PM Audit Round 57 — fix:
IncomeExpensesPage empty-state messages for the income and expense tabs used
"imported" — e.g. "check if income transactions have been imported." Users
connect banks and the system syncs transactions automatically; they don't
"import" anything. Changed to "add transactions to your account." which
describes what users can actually do.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"

_FILE = (
    FRONTEND
    / "features/income-expenses/pages/IncomeExpensesPage.tsx"
)


def _src():
    return _FILE.read_text()


# ── IncomeExpensesPage: no "imported" jargon ─────────────────────────────────


def test_no_income_transactions_imported_copy():
    src = _src()
    assert "income transactions have been imported" not in src


def test_no_expense_transactions_imported_copy():
    src = _src()
    assert "expense transactions have been imported" not in src


def test_income_empty_state_actionable_copy():
    src = _src()
    assert "add transactions to your account" in src
