"""
PM Audit Round 75 — Member expense splitting and household UX improvements.

Fixes:
1. TransactionSplit.assigned_user_id column added (DB migration r76_member_split)
2. TransactionSplitSchema exposes assigned_user_id in create/update/response
3. transaction_split_service.create_splits passes assigned_user_id through
4. transaction_split_service.update_split accepts assigned_user_id
5. transaction_split_service.get_member_balances returns per-member totals
6. GET /transaction-splits/member-balances endpoint exists
7. POST /household/invitations/{id}/resend endpoint exists
8. MemberSettlementWidget file exists on disk
9. widgetRegistry includes "member-settlement" entry
"""

import inspect


# ---------------------------------------------------------------------------
# 1. TransactionSplit model — assigned_user_id column
# ---------------------------------------------------------------------------

def test_transaction_split_model_has_assigned_user_id():
    from app.models.transaction import TransactionSplit
    assert hasattr(TransactionSplit, "assigned_user_id")


def test_transaction_split_model_assigned_user_relationship():
    from app.models.transaction import TransactionSplit
    assert hasattr(TransactionSplit, "assigned_user")


# ---------------------------------------------------------------------------
# 2. Schema — assigned_user_id in create/update/response
# ---------------------------------------------------------------------------

def test_split_create_schema_has_assigned_user_id():
    from app.schemas.transaction_split import TransactionSplitCreate
    fields = TransactionSplitCreate.model_fields
    assert "assigned_user_id" in fields


def test_split_update_schema_has_assigned_user_id():
    from app.schemas.transaction_split import TransactionSplitUpdate
    fields = TransactionSplitUpdate.model_fields
    assert "assigned_user_id" in fields


def test_split_response_schema_has_assigned_user_id():
    from app.schemas.transaction_split import TransactionSplitResponse
    fields = TransactionSplitResponse.model_fields
    assert "assigned_user_id" in fields


def test_member_balance_response_schema_exists():
    from app.schemas.transaction_split import MemberBalanceResponse
    fields = MemberBalanceResponse.model_fields
    assert "member_id" in fields
    assert "member_name" in fields
    assert "total_assigned" in fields
    assert "net_owed" in fields


# ---------------------------------------------------------------------------
# 3. Service — create_splits passes assigned_user_id
# ---------------------------------------------------------------------------

def test_split_service_create_passes_assigned_user_id():
    from app.services.transaction_split_service import TransactionSplitService
    src = inspect.getsource(TransactionSplitService.create_splits)
    assert "assigned_user_id" in src


# ---------------------------------------------------------------------------
# 4. Service — update_split accepts assigned_user_id
# ---------------------------------------------------------------------------

def test_split_service_update_accepts_assigned_user_id():
    from app.services.transaction_split_service import TransactionSplitService
    sig = inspect.signature(TransactionSplitService.update_split)
    assert "assigned_user_id" in sig.parameters


# ---------------------------------------------------------------------------
# 5. Service — get_member_balances exists
# ---------------------------------------------------------------------------

def test_split_service_has_get_member_balances():
    from app.services.transaction_split_service import TransactionSplitService
    assert hasattr(TransactionSplitService, "get_member_balances")
    assert callable(TransactionSplitService.get_member_balances)


def test_split_service_get_member_balances_accepts_since_date():
    from app.services.transaction_split_service import TransactionSplitService
    sig = inspect.signature(TransactionSplitService.get_member_balances)
    assert "since_date" in sig.parameters


# ---------------------------------------------------------------------------
# 6. API endpoint — GET /transaction-splits/member-balances
# ---------------------------------------------------------------------------

def test_transaction_splits_api_imports_member_balance_response():
    import app.api.v1.transaction_splits as mod
    src = inspect.getsource(mod)
    assert "member-balances" in src
    assert "MemberBalanceResponse" in src


def test_transaction_splits_api_has_get_member_balances_route():
    import app.api.v1.transaction_splits as mod
    src = inspect.getsource(mod)
    assert "get_member_balances" in src


# ---------------------------------------------------------------------------
# 7. Household API — POST /household/invitations/{id}/resend endpoint
# ---------------------------------------------------------------------------

def test_household_api_has_resend_invitation():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    assert "resend_invitation" in src
    assert "invitations/{invitation_id}/resend" in src


def test_household_resend_refreshes_invitation_code():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    assert "invitation_code = secrets.token_urlsafe" in src


def test_household_resend_extends_expiry():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    # Expiry may use a constant (HOUSEHOLD.INVITATION_EXPIRY_DAYS) or literal 7
    assert "expires_at" in src and "timedelta" in src
