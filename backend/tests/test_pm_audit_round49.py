"""
PM Audit Round 49 — fixes:
1. SS Optimizer: "Analyse" button label was British English.
   Changed to "Analyze" (US English, consistent with the rest of the app).
2. SS Optimizer: returning users saw a blank results section on page load because
   `submitted` was initialized to `false` regardless of persisted localStorage values.
   Fixed to auto-submit on load when a previously-saved salary exists in localStorage,
   so returning users immediately see their last results without clicking Analyze again.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _ss_src():
    return (FRONTEND / "pages/SSClaimingPage.tsx").read_text()


# ── 1. Button label: American English ────────────────────────────────────────


def test_ss_button_says_analyze_not_analyse():
    src = _ss_src()
    assert "Analyse" not in src


def test_ss_button_says_analyze():
    src = _ss_src()
    assert "Analyze" in src


# ── 2. Auto-submit on load when salary is persisted ──────────────────────────


def test_ss_submitted_not_hard_coded_false():
    src = _ss_src()
    # Old code: useState(false)  — should no longer exist for submitted
    # (still allowed elsewhere, but not for the submitted state init on its own line)
    assert "useState(false)" not in src


def test_ss_submitted_reads_localstorage_on_init():
    src = _ss_src()
    # The submitted initializer must reference localStorage to restore previous state
    idx = src.index("const [submitted, setSubmitted]")
    surrounding = src[idx : idx + 200]
    assert "localStorage" in surrounding


def test_ss_submitted_checks_salary_in_init():
    src = _ss_src()
    idx = src.index("const [submitted, setSubmitted]")
    surrounding = src[idx : idx + 200]
    assert "ss-salary" in surrounding
