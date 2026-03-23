"""
PM Audit Round 53 — fix:
The "investments unlocked" discovery toast referenced "Investment Health under Analytics"
— but the Investment Health page was merged into /investments and the route
/investment-health now redirects to /investments. There is no "Investment Health" item
in the Analytics nav dropdown.

Updated the toast description to correctly say "Tax Deductible under Analytics, and
fund fee/expense ratio analysis on the Investments page."
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _layout_src():
    return (FRONTEND / "components/Layout.tsx").read_text()


# ── investments-nav toast description ────────────────────────────────────────


def test_investments_toast_no_stale_investment_health_nav_copy():
    src = _layout_src()
    # The old text referenced a nav item that no longer exists
    assert "Investment Health under Analytics" not in src


def test_investments_toast_mentions_tax_deductible():
    src = _layout_src()
    idx = src.index('"investments-nav"')
    surrounding = src[idx : idx + 300]
    assert "Tax Deductible" in surrounding


def test_investments_toast_mentions_investments_page():
    src = _layout_src()
    idx = src.index('"investments-nav"')
    surrounding = src[idx : idx + 300]
    assert "Investments page" in surrounding
