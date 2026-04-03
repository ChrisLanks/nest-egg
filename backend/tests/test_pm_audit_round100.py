"""
PM Audit Round 100 — Promote lazy inline rate_limit_service imports to module-level.

Changes covered:
1. reports.py: remove 3 inline `from app.services.rate_limit_service import rate_limit_service as _rls`
2. retirement.py: remove 2 inline imports; add top-level import
3. transactions.py: remove 2 inline imports; add top-level import
"""

import inspect


def _has_no_inline_rls_import(mod):
    src = inspect.getsource(mod)
    return 'import rate_limit_service as _rls' not in src


def _has_toplevel_rate_limit(mod):
    src = inspect.getsource(mod)
    return 'from app.services.rate_limit_service import rate_limit_service' in src


def test_reports_no_inline_rate_limit_imports():
    import app.api.v1.reports as mod
    assert _has_no_inline_rls_import(mod)


def test_reports_has_toplevel_rate_limit():
    import app.api.v1.reports as mod
    assert _has_toplevel_rate_limit(mod)


def test_retirement_no_inline_rate_limit_imports():
    import app.api.v1.retirement as mod
    assert _has_no_inline_rls_import(mod)


def test_retirement_has_toplevel_rate_limit():
    import app.api.v1.retirement as mod
    assert _has_toplevel_rate_limit(mod)


def test_transactions_no_inline_rate_limit_imports():
    import app.api.v1.transactions as mod
    assert _has_no_inline_rls_import(mod)


def test_transactions_has_toplevel_rate_limit():
    import app.api.v1.transactions as mod
    assert _has_toplevel_rate_limit(mod)
