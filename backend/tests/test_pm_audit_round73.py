"""
PM Audit Round 73 — Frontend seeding extended to FireMetricsPage and SSClaimingPage.

Fixes:
1. FireMetricsPage.tsx seeds withdrawalRate/expectedReturn/retirementAge from
   /settings/financial-defaults when no localStorage entry exists
2. SSClaimingPage.tsx seeds salary and plannedRetirementAge from
   /settings/financial-defaults when no localStorage entry exists
"""

import os

FRONTEND = os.path.join(os.path.dirname(__file__), "../../frontend/src")


def _read(rel: str) -> str:
    return open(os.path.join(FRONTEND, rel), encoding="utf-8").read()


# ---------------------------------------------------------------------------
# FireMetricsPage
# ---------------------------------------------------------------------------

def test_fire_metrics_page_fetches_financial_defaults():
    src = _read("pages/FireMetricsPage.tsx")
    assert "/settings/financial-defaults" in src


def test_fire_metrics_page_has_from_storage_flag():
    src = _read("pages/FireMetricsPage.tsx")
    assert "_fromStorage" in src


def test_fire_metrics_page_seeds_withdrawal_rate():
    src = _read("pages/FireMetricsPage.tsx")
    assert "default_withdrawal_rate" in src


def test_fire_metrics_page_seeds_expected_return():
    src = _read("pages/FireMetricsPage.tsx")
    assert "default_expected_return" in src


def test_fire_metrics_page_seeds_retirement_age():
    src = _read("pages/FireMetricsPage.tsx")
    assert "default_retirement_age" in src


# ---------------------------------------------------------------------------
# SSClaimingPage
# ---------------------------------------------------------------------------

def test_ss_claiming_page_fetches_financial_defaults():
    src = _read("pages/SSClaimingPage.tsx")
    assert "/settings/financial-defaults" in src


def test_ss_claiming_page_no_bare_80000_default():
    src = _read("pages/SSClaimingPage.tsx")
    # The bare "80000" localStorage default should be gone
    assert 'useLocalStorage("ss-salary", "80000")' not in src


def test_ss_claiming_page_no_bare_65_retirement_default():
    src = _read("pages/SSClaimingPage.tsx")
    assert 'useLocalStorage(\n    "ss-planned-retirement-age",\n    "65"' not in src
    assert '"ss-planned-retirement-age",\n    "65",' not in src


def test_ss_claiming_page_seeds_salary_from_defaults():
    src = _read("pages/SSClaimingPage.tsx")
    assert "default_annual_spending" in src


def test_ss_claiming_page_seeds_retirement_age_from_defaults():
    src = _read("pages/SSClaimingPage.tsx")
    assert "default_retirement_age" in src


def test_ss_claiming_page_has_from_storage_guard():
    src = _read("pages/SSClaimingPage.tsx")
    # Uses localStorage.getItem check before calling API
    assert "ss-salary" in src
    assert "hasSalary" in src or "localStorage.getItem" in src
