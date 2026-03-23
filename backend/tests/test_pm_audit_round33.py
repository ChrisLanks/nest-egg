"""
PM Audit Round 33 — fixes:
1. WelcomePage invite step: JSX fragment wrapper added around FormControl +
   "Continue without inviting" button (missing fragment caused a build error
   since React ternary else branches can only return one root element)
2. "Continue without inviting" button now calls next() instead of setStep(3)
   directly, ensuring it goes through the standard step-advance logic
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


# ── 1. JSX fragment wraps both elements in else branch ───────────────────────


def test_invite_else_branch_has_fragment():
    src = _welcome_src()
    # The fragment (<>) must appear before FormControl in the ternary else branch
    # Look at the whole invite step block
    invite_idx = src.index("Continue without inviting")
    surrounding = src[invite_idx - 1400 : invite_idx + 300]
    assert "<>" in surrounding


def test_invite_form_control_and_button_are_siblings():
    src = _welcome_src()
    # Both FormControl and the skip button must be inside a single <> fragment
    skip_idx = src.index("Continue without inviting")
    # Fragment opens before FormControl and closes after the skip button
    surrounding = src[skip_idx - 1400 : skip_idx + 300]
    assert "<>" in surrounding
    assert "</>" in surrounding


def test_no_bare_sibling_jsx_in_ternary():
    src = _welcome_src()
    # The old bug: </FormControl> immediately followed by <Button (no fragment)
    # This would cause a JSX parse error. It must not exist.
    assert "</FormControl>\n              <Button" not in src


# ── 2. "Continue without inviting" calls next() ──────────────────────────────


def test_continue_without_inviting_calls_next():
    src = _welcome_src()
    skip_idx = src.index("Continue without inviting")
    surrounding = src[skip_idx - 100 : skip_idx + 100]
    assert "onClick={next}" in surrounding


def test_continue_without_inviting_does_not_call_set_step():
    src = _welcome_src()
    skip_idx = src.index("Continue without inviting")
    surrounding = src[skip_idx - 100 : skip_idx + 100]
    # setStep(3) was the old direct jump, bypassing next() logic
    assert "setStep(3)" not in surrounding
