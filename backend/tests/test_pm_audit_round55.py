"""
PM Audit Round 55 — fix:
AccountDetailPage VIN hint text exposed internal third-party API name to users:
"17-character VIN enables automatic market value updates via MarketCheck API."
Users have no need to know which API provider is used; removed the "via MarketCheck API"
clause so the text simply says: "17-character VIN enables automatic market value updates."
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _account_detail_src():
    return (FRONTEND / "pages/AccountDetailPage.tsx").read_text()


# ── VIN hint text ─────────────────────────────────────────────────────────────


def test_vin_hint_no_marketcheck_api():
    src = _account_detail_src()
    assert "MarketCheck API" not in src


def test_vin_hint_no_via_api_reference():
    src = _account_detail_src()
    # No internal API provider name should appear in user-facing copy
    assert "via MarketCheck" not in src


def test_vin_hint_still_mentions_market_value_updates():
    src = _account_detail_src()
    assert "automatic market value updates" in src
