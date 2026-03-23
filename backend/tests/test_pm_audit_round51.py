"""
PM Audit Round 51 — fixes:
1. TaxProjectionPage: "safe harbour" (British English) → "safe harbor" (American English).
   This appeared in the form label, the tooltip, and both alert messages. Tax terminology
   in the US always uses "safe harbor" (IRS Publication 505, Form 1040-ES).
2. RothConversionPage: "minimise" (British) → "minimize" (American) in the page subtitle.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _tax_src():
    return (FRONTEND / "pages/TaxProjectionPage.tsx").read_text()


def _roth_src():
    return (FRONTEND / "pages/RothConversionPage.tsx").read_text()


# ── 1. Tax Projection: safe harbor spelling ───────────────────────────────────


def test_tax_no_safe_harbour_in_user_text():
    src = _tax_src()
    # User-visible strings and labels must use American spelling
    # (variable names like safe_harbour_amount are API fields — those stay)
    assert "safe harbour" not in src
    assert "Safe harbour" not in src


def test_tax_uses_safe_harbor():
    src = _tax_src()
    assert "safe harbor" in src


def test_tax_form_label_uses_safe_harbor():
    src = _tax_src()
    # The form label for the prior-year tax field
    assert "for safe harbor" in src


def test_tax_alert_messages_use_safe_harbor():
    src = _tax_src()
    # Both the "within" and "exceeds" alert messages
    assert "within safe harbor" in src
    assert "exceeds safe harbor" in src


# ── 2. Roth Conversion: minimize spelling ─────────────────────────────────────


def test_roth_no_minimise():
    src = _roth_src()
    assert "minimise" not in src


def test_roth_uses_minimize():
    src = _roth_src()
    assert "minimize" in src
