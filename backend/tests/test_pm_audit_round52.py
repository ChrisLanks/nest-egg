"""
PM Audit Round 52 — fix:
Rental Properties empty state used developer-speak ("Set 'Is Rental Property' to
true on any property account") which is confusing for non-technical users. The actual
user flow is to add a property account and choose "Investment Property" as the
classification — no internal boolean flag is exposed.

Updated to: 'Add a property account and set its classification to "Investment Property"
to track rental income, expenses, and net operating income here.'
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _rental_src():
    return (FRONTEND / "pages/RentalPropertiesPage.tsx").read_text()


# ── Rental Properties empty state copy ───────────────────────────────────────


def test_rental_empty_state_no_developer_speak():
    src = _rental_src()
    # Old confusing instruction referencing internal boolean
    assert '"Is Rental Property"' not in src


def test_rental_empty_state_no_set_to_true():
    src = _rental_src()
    assert "Set" not in src or "true on any property account" not in src


def test_rental_empty_state_mentions_investment_property():
    src = _rental_src()
    assert "Investment Property" in src


def test_rental_empty_state_mentions_add_account():
    src = _rental_src()
    idx = src.index("Investment Property")
    surrounding = src[idx - 200 : idx + 100]
    assert "add" in surrounding.lower() or "Add" in surrounding
