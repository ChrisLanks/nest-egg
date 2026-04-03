"""
PM Audit Round 95 — Typed response models + sanitization for pe_performance/hsa/transactions.

Changes covered:
1. pe_performance.py: PETransactionResponse on POST /{account_id}/transactions;
   router-level _rate_limit; sanitize notes on create
2. hsa.py: HsaAttachmentResponse on POST /receipts/{receipt_id}/attachment
3. transactions.py: LabelActionResponse on POST /{transaction_id}/labels/{label_id}
"""

import inspect


# ---------------------------------------------------------------------------
# 1. pe_performance.py
# ---------------------------------------------------------------------------

def test_pe_performance_has_router_rate_limit():
    import app.api.v1.pe_performance as mod
    src = inspect.getsource(mod)
    assert "_rate_limit" in src
    assert "dependencies=[Depends(_rate_limit)]" in src


def test_pe_performance_imports_sanitization():
    import app.api.v1.pe_performance as mod
    src = inspect.getsource(mod)
    assert "input_sanitization_service" in src


def test_pe_performance_add_transaction_sanitizes_notes():
    import app.api.v1.pe_performance as mod
    src = inspect.getsource(mod.add_pe_transaction)
    assert "sanitize_html" in src
    assert "notes" in src


def test_pe_performance_add_transaction_has_response_model():
    import app.api.v1.pe_performance as mod
    src = inspect.getsource(mod)
    assert "response_model=PETransactionResponse" in src


def test_pe_performance_add_transaction_returns_model():
    import app.api.v1.pe_performance as mod
    src = inspect.getsource(mod.add_pe_transaction)
    assert "PETransactionResponse(" in src


# ---------------------------------------------------------------------------
# 2. hsa.py — attachment response
# ---------------------------------------------------------------------------

def test_hsa_has_attachment_response():
    import app.api.v1.hsa as mod
    assert hasattr(mod, "HsaAttachmentResponse")
    fields = mod.HsaAttachmentResponse.model_fields
    assert "id" in fields
    assert "file_name" in fields
    assert "file_content_type" in fields


def test_hsa_attachment_upload_has_response_model():
    import app.api.v1.hsa as mod
    src = inspect.getsource(mod)
    assert "response_model=HsaAttachmentResponse" in src


def test_hsa_attachment_upload_returns_model():
    import app.api.v1.hsa as mod
    src = inspect.getsource(mod.upload_receipt_attachment)
    assert "HsaAttachmentResponse(" in src


# ---------------------------------------------------------------------------
# 3. transactions.py — LabelActionResponse
# ---------------------------------------------------------------------------

def test_transactions_has_label_action_response():
    import app.api.v1.transactions as mod
    assert hasattr(mod, "LabelActionResponse")
    fields = mod.LabelActionResponse.model_fields
    assert "message" in fields


def test_transactions_add_label_has_response_model():
    import app.api.v1.transactions as mod
    src = inspect.getsource(mod)
    assert "response_model=LabelActionResponse" in src


def test_transactions_add_label_returns_model():
    import app.api.v1.transactions as mod
    src = inspect.getsource(mod.add_label_to_transaction)
    assert "LabelActionResponse(" in src
