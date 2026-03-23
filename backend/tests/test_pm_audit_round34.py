"""
PM Audit Round 34 — fixes:
1. WelcomePage step 1 (connect accounts): heading and CTA button are now
   goal-aware — investments goal users see "Connect Your Investment Account"
   and "Connect an Investment Account" instead of the generic bank copy
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _welcome_src():
    return (FRONTEND / "pages/WelcomePage.tsx").read_text()


# ── 1. Step 1 heading and button adapt to investments goal ───────────────────


def test_step1_heading_is_goal_aware():
    src = _welcome_src()
    assert "Connect Your Investment Account" in src


def test_step1_heading_investments_condition():
    src = _welcome_src()
    # The heading uses selectedGoal === "investments" as a ternary condition
    invest_heading_idx = src.index("Connect Your Investment Account")
    surrounding = src[invest_heading_idx - 100 : invest_heading_idx + 50]
    assert 'selectedGoal === "investments"' in surrounding


def test_step1_button_investments_label():
    src = _welcome_src()
    assert "Connect an Investment Account" in src


def test_step1_button_investments_condition():
    src = _welcome_src()
    invest_btn_idx = src.index("Connect an Investment Account")
    surrounding = src[invest_btn_idx - 100 : invest_btn_idx + 50]
    assert 'selectedGoal === "investments"' in surrounding


def test_step1_fallback_bank_label_still_present():
    src = _welcome_src()
    # The default (non-investments) label must still be there
    assert "Connect a Bank Account" in src


def test_step1_description_is_goal_aware():
    src = _welcome_src()
    # Investments users get a portfolio-focused description
    assert "401(k), IRA, or brokerage" in src
