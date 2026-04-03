"""
PM Audit Round 92 — Typed response models + router rate limit for
transaction_merges and recurring_transactions.

Changes covered:
1. transaction_merges.py: FindDuplicatesResponse + AutoDetectResponse models;
   router-level _rate_limit; response_model on find-duplicates + auto-detect endpoints
2. recurring_transactions.py: DetectResponse + ApplyLabelResponse + PreviewLabelResponse;
   router-level _rate_limit; response_model on detect + apply-label + preview-label endpoints
"""

import inspect


# ---------------------------------------------------------------------------
# 1. transaction_merges.py
# ---------------------------------------------------------------------------

def test_transaction_merges_has_find_duplicates_response():
    import app.api.v1.transaction_merges as mod
    assert hasattr(mod, "FindDuplicatesResponse")
    fields = mod.FindDuplicatesResponse.model_fields
    assert "transaction_id" in fields
    assert "potential_duplicates" in fields
    assert "count" in fields


def test_transaction_merges_has_auto_detect_response():
    import app.api.v1.transaction_merges as mod
    assert hasattr(mod, "AutoDetectResponse")
    fields = mod.AutoDetectResponse.model_fields
    assert "dry_run" in fields
    assert "matches_found" in fields
    assert "matches" in fields


def test_transaction_merges_has_router_rate_limit():
    import app.api.v1.transaction_merges as mod
    src = inspect.getsource(mod)
    assert "_rate_limit" in src
    assert "dependencies=[Depends(_rate_limit)]" in src


def test_transaction_merges_find_duplicates_has_response_model():
    import app.api.v1.transaction_merges as mod
    src = inspect.getsource(mod)
    assert "response_model=FindDuplicatesResponse" in src


def test_transaction_merges_auto_detect_has_response_model():
    import app.api.v1.transaction_merges as mod
    src = inspect.getsource(mod)
    assert "response_model=AutoDetectResponse" in src


def test_transaction_merges_find_duplicates_returns_model():
    import app.api.v1.transaction_merges as mod
    src = inspect.getsource(mod.find_potential_duplicates)
    assert "FindDuplicatesResponse(" in src


def test_transaction_merges_auto_detect_returns_model():
    import app.api.v1.transaction_merges as mod
    src = inspect.getsource(mod.auto_detect_and_merge_duplicates)
    assert "AutoDetectResponse(" in src


# ---------------------------------------------------------------------------
# 2. recurring_transactions.py
# ---------------------------------------------------------------------------

def test_recurring_has_detect_response():
    import app.api.v1.recurring_transactions as mod
    assert hasattr(mod, "DetectResponse")
    fields = mod.DetectResponse.model_fields
    assert "detected_patterns" in fields
    assert "patterns" in fields


def test_recurring_has_apply_label_response():
    import app.api.v1.recurring_transactions as mod
    assert hasattr(mod, "ApplyLabelResponse")
    fields = mod.ApplyLabelResponse.model_fields
    assert "applied_count" in fields
    assert "label_id" in fields


def test_recurring_has_preview_label_response():
    import app.api.v1.recurring_transactions as mod
    assert hasattr(mod, "PreviewLabelResponse")
    fields = mod.PreviewLabelResponse.model_fields
    assert "matching_transactions" in fields


def test_recurring_has_router_rate_limit():
    import app.api.v1.recurring_transactions as mod
    src = inspect.getsource(mod)
    assert "_rate_limit" in src
    assert "dependencies=[Depends(_rate_limit)]" in src


def test_recurring_detect_has_response_model():
    import app.api.v1.recurring_transactions as mod
    src = inspect.getsource(mod)
    assert "response_model=DetectResponse" in src


def test_recurring_apply_label_has_response_model():
    import app.api.v1.recurring_transactions as mod
    src = inspect.getsource(mod)
    assert "response_model=ApplyLabelResponse" in src


def test_recurring_preview_label_has_response_model():
    import app.api.v1.recurring_transactions as mod
    src = inspect.getsource(mod)
    assert "response_model=PreviewLabelResponse" in src


def test_recurring_detect_returns_model():
    import app.api.v1.recurring_transactions as mod
    src = inspect.getsource(mod.detect_recurring_patterns)
    assert "DetectResponse(" in src


def test_recurring_apply_label_returns_model():
    import app.api.v1.recurring_transactions as mod
    src = inspect.getsource(mod.apply_label_to_recurring)
    assert "ApplyLabelResponse(" in src


def test_recurring_preview_label_returns_model():
    import app.api.v1.recurring_transactions as mod
    src = inspect.getsource(mod.preview_label_matches)
    assert "PreviewLabelResponse(" in src
