"""
PM Audit Round 101 — fixes:
1. Fix response_model mismatches: GET endpoints that return lists were
   incorrectly annotated with response_model=Dict[str, Any] (introduced by
   round 99 batch script). Changed to response_model=List[Any] on:
   - GET /labels/tax-deductible (labels.py)
   - GET /stress-test/scenarios (stress_test.py)
   - GET /estate/beneficiaries (estate.py)
   - GET /estate/documents (estate.py)
   - GET /hsa/receipts (hsa.py)
   - GET /debt-payoff/debts (debt_payoff.py)
   - GET /charitable-giving/labels (charitable_giving.py)
2. Restore retirement.py from round 100 batch-script corruption that
   replaced the retirement planner with the Reports API stub, causing
   404 on /api/v1/retirement/scenarios.
"""
import inspect
from pathlib import Path

BACKEND = Path(__file__).parent.parent


def _src(filename: str) -> str:
    return (BACKEND / f"app/api/v1/{filename}").read_text()


# ── 1. List-returning endpoints use List[Any] not Dict[str, Any] ─────────────


def test_labels_tax_deductible_uses_list_response_model():
    src = _src("labels.py")
    idx = src.index('"/tax-deductible"')
    decorator = src[idx - 50 : idx + 80]
    assert "List[Any]" in decorator
    assert 'response_model=Dict[str, Any]' not in decorator


def test_stress_test_scenarios_uses_list_response_model():
    src = _src("stress_test.py")
    idx = src.index('"/scenarios"')
    decorator = src[max(0, idx - 150) : idx + 200]
    assert "List[Any]" in decorator
    assert 'response_model=Dict[str, Any]' not in decorator


def test_estate_beneficiaries_uses_list_response_model():
    src = _src("estate.py")
    idx = src.index('"/beneficiaries"')
    decorator = src[max(0, idx - 100) : idx + 100]
    assert "List[Any]" in decorator


def test_estate_documents_uses_list_response_model():
    src = _src("estate.py")
    # Find the second occurrence (list_documents)
    idx1 = src.index('"/documents"')
    decorator = src[max(0, idx1 - 100) : idx1 + 100]
    assert "List[Any]" in decorator


def test_hsa_receipts_uses_list_response_model():
    src = _src("hsa.py")
    idx = src.index('"/receipts"')
    decorator = src[max(0, idx - 150) : idx + 150]
    assert "List[Any]" in decorator
    assert 'response_model=Dict[str, Any]' not in decorator


def test_debt_payoff_debts_uses_list_response_model():
    src = _src("debt_payoff.py")
    idx = src.index('"/debts"')
    decorator = src[max(0, idx - 50) : idx + 80]
    assert "List[Any]" in decorator
    assert 'response_model=Dict[str, Any]' not in decorator


def test_charitable_giving_labels_uses_list_response_model():
    src = _src("charitable_giving.py")
    idx = src.index('"/labels"')
    decorator = src[max(0, idx - 50) : idx + 80]
    assert "List[Any]" in decorator
    assert 'response_model=Dict[str, Any]' not in decorator


# ── 2. Retirement planner routes are present ─────────────────────────────────


def test_retirement_planner_scenarios_endpoint_exists():
    src = _src("retirement.py")
    assert '"/scenarios"' in src or "'/scenarios'" in src


def test_retirement_planner_is_not_reports_api():
    src = _src("retirement.py")
    # Reports API has these — retirement planner should not
    assert "ReportTemplate" not in src
    assert "list_report_templates" not in src


def test_retirement_planner_has_monte_carlo():
    src = _src("retirement.py")
    assert "RetirementMonteCarloService" in src or "monte_carlo" in src.lower()
