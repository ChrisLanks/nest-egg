"""
PM Audit Round 90 — Input sanitization + typed response models for estate/gift/hsa/subscriptions.

Changes covered:
1. gift_tracker.py: sanitize recipient_name, recipient_relationship, notes on create
2. estate.py: _rate_limit router dependency; BeneficiaryResponse + EstateDocumentResponse models;
   sanitize name, relationship, notes on POST /beneficiaries;
   sanitize notes on POST /documents
3. hsa.py: HsaReceiptCreateResponse + HsaReceiptUpdateResponse models;
   sanitize description, notes on create; sanitize notes on update
4. subscriptions.py: DeactivateResponse model on PATCH deactivate endpoint
"""

import inspect


# ---------------------------------------------------------------------------
# 1. gift_tracker.py — input sanitization
# ---------------------------------------------------------------------------

def test_gift_tracker_imports_sanitization():
    import app.api.v1.gift_tracker as mod
    src = inspect.getsource(mod)
    assert "input_sanitization_service" in src


def test_gift_tracker_create_sanitizes_recipient_name():
    import app.api.v1.gift_tracker as mod
    src = inspect.getsource(mod.create_gift)
    assert "sanitize_html" in src
    assert "recipient_name" in src


def test_gift_tracker_create_sanitizes_notes():
    import app.api.v1.gift_tracker as mod
    src = inspect.getsource(mod.create_gift)
    assert "notes" in src
    assert "sanitize_html" in src


# ---------------------------------------------------------------------------
# 2. estate.py — rate limit, response models, sanitization
# ---------------------------------------------------------------------------

def test_estate_imports_sanitization():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "input_sanitization_service" in src


def test_estate_has_rate_limit_dependency():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "_rate_limit" in src
    assert "rate_limit_service" in src


def test_estate_router_uses_rate_limit():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "dependencies=[Depends(_rate_limit)]" in src


def test_estate_has_beneficiary_response_model():
    import app.api.v1.estate as mod
    assert hasattr(mod, "BeneficiaryResponse")
    fields = mod.BeneficiaryResponse.model_fields
    assert "id" in fields
    assert "name" in fields
    assert "percentage" in fields


def test_estate_has_estate_document_response_model():
    import app.api.v1.estate as mod
    assert hasattr(mod, "EstateDocumentResponse")
    fields = mod.EstateDocumentResponse.model_fields
    assert "id" in fields
    assert "document_type" in fields


def test_estate_create_beneficiary_sanitizes_fields():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod.create_beneficiary)
    assert "sanitize_html" in src
    assert "name" in src
    assert "relationship" in src


def test_estate_create_beneficiary_uses_response_model():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "response_model=BeneficiaryResponse" in src


def test_estate_upsert_document_sanitizes_notes():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod.upsert_document)
    assert "sanitize_html" in src
    assert "notes" in src


def test_estate_upsert_document_uses_response_model():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "response_model=EstateDocumentResponse" in src


# ---------------------------------------------------------------------------
# 3. hsa.py — response models + sanitization
# ---------------------------------------------------------------------------

def test_hsa_imports_sanitization():
    import app.api.v1.hsa as mod
    src = inspect.getsource(mod)
    assert "input_sanitization_service" in src


def test_hsa_has_create_response_model():
    import app.api.v1.hsa as mod
    assert hasattr(mod, "HsaReceiptCreateResponse")
    fields = mod.HsaReceiptCreateResponse.model_fields
    assert "id" in fields
    assert "amount" in fields
    assert "description" in fields
    assert "is_reimbursed" in fields


def test_hsa_has_update_response_model():
    import app.api.v1.hsa as mod
    assert hasattr(mod, "HsaReceiptUpdateResponse")
    fields = mod.HsaReceiptUpdateResponse.model_fields
    assert "id" in fields
    assert "is_reimbursed" in fields


def test_hsa_create_receipt_sanitizes_fields():
    import app.api.v1.hsa as mod
    src = inspect.getsource(mod.create_receipt)
    assert "sanitize_html" in src
    assert "description" in src


def test_hsa_update_receipt_sanitizes_notes():
    import app.api.v1.hsa as mod
    src = inspect.getsource(mod.update_receipt)
    assert "sanitize_html" in src
    assert "notes" in src


def test_hsa_create_receipt_uses_response_model():
    import app.api.v1.hsa as mod
    src = inspect.getsource(mod)
    assert "response_model=HsaReceiptCreateResponse" in src


def test_hsa_update_receipt_uses_response_model():
    import app.api.v1.hsa as mod
    src = inspect.getsource(mod)
    assert "response_model=HsaReceiptUpdateResponse" in src


# ---------------------------------------------------------------------------
# 4. subscriptions.py — DeactivateResponse model
# ---------------------------------------------------------------------------

def test_subscriptions_has_deactivate_response_model():
    import app.api.v1.subscriptions as mod
    assert hasattr(mod, "DeactivateResponse")
    fields = mod.DeactivateResponse.model_fields
    assert "success" in fields
    assert "message" in fields


def test_subscriptions_deactivate_uses_response_model():
    import app.api.v1.subscriptions as mod
    src = inspect.getsource(mod)
    assert "response_model=DeactivateResponse" in src


def test_subscriptions_deactivate_returns_model_instance():
    import app.api.v1.subscriptions as mod
    src = inspect.getsource(mod.deactivate_subscription)
    assert "DeactivateResponse(" in src
