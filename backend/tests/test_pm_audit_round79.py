"""
PM Audit Round 79 — Settlement UX + notification triggers + threshold constants.

Changes covered:
1. financial.py: new SMART_INSIGHTS class with FEE_DRAG_THRESHOLD,
   CONCENTRATION_THRESHOLD, CONCENTRATION_MIN_VALUE, SETTLEMENT_EVEN_BAND
2. smart_insights_service.py: class-level thresholds reference SMART_INSIGHTS
3. transaction_split_service.py: fires EXPENSE_SPLIT_ASSIGNED notification
   when assigned_user_id != creator; imports NotificationService
4. transaction.py: TransactionSplit gains settled_at column
5. transaction_split.py (schema): SettleRequest, SettleResponse added;
   TransactionSplitResponse gains settled_at
6. transaction_splits.py (API): POST /transaction-splits/settle endpoint
7. Migration r78_add_settled_at adds settled_at to transaction_splits
8. settle_member service method fires SETTLEMENT_REMINDER notification
"""

import inspect


# ---------------------------------------------------------------------------
# 1. SMART_INSIGHTS constants in financial.py
# ---------------------------------------------------------------------------

def test_smart_insights_class_exists():
    from app.constants.financial import SMART_INSIGHTS
    assert hasattr(SMART_INSIGHTS, "FEE_DRAG_THRESHOLD")
    assert hasattr(SMART_INSIGHTS, "CONCENTRATION_THRESHOLD")
    assert hasattr(SMART_INSIGHTS, "CONCENTRATION_MIN_VALUE")
    assert hasattr(SMART_INSIGHTS, "SETTLEMENT_EVEN_BAND")


def test_smart_insights_fee_drag_threshold_value():
    from app.constants.financial import SMART_INSIGHTS
    assert SMART_INSIGHTS.FEE_DRAG_THRESHOLD == 0.003


def test_smart_insights_concentration_threshold_value():
    from app.constants.financial import SMART_INSIGHTS
    assert SMART_INSIGHTS.CONCENTRATION_THRESHOLD == 0.10


def test_smart_insights_concentration_min_value():
    from app.constants.financial import SMART_INSIGHTS
    assert SMART_INSIGHTS.CONCENTRATION_MIN_VALUE == 10_000


def test_smart_insights_settlement_even_band():
    from app.constants.financial import SMART_INSIGHTS
    assert SMART_INSIGHTS.SETTLEMENT_EVEN_BAND == 0.005


# ---------------------------------------------------------------------------
# 2. smart_insights_service.py — no bare hardcoded threshold literals
# ---------------------------------------------------------------------------

def test_smart_insights_service_imports_smart_insights_constant():
    import app.services.smart_insights_service as mod
    src = inspect.getsource(mod)
    assert "SMART_INSIGHTS" in src


def test_smart_insights_service_no_bare_fee_drag_literal():
    import app.services.smart_insights_service as mod
    src = inspect.getsource(mod)
    # The threshold must NOT be a bare literal assignment anymore
    assert "_FEE_DRAG_THRESHOLD = 0.003" not in src


def test_smart_insights_service_no_bare_concentration_literal():
    import app.services.smart_insights_service as mod
    src = inspect.getsource(mod)
    assert "_CONCENTRATION_THRESHOLD = 0.10" not in src


def test_smart_insights_service_no_bare_min_value_literal():
    import app.services.smart_insights_service as mod
    src = inspect.getsource(mod)
    assert "_CONCENTRATION_MIN_VALUE = 10_000" not in src


# ---------------------------------------------------------------------------
# 3. transaction_split_service.py — imports NotificationService
# ---------------------------------------------------------------------------

def test_transaction_split_service_imports_notification_service():
    import app.services.transaction_split_service as mod
    src = inspect.getsource(mod)
    assert "NotificationService" in src


def test_transaction_split_service_imports_notification_type():
    import app.services.transaction_split_service as mod
    src = inspect.getsource(mod)
    assert "NotificationType" in src


def test_transaction_split_service_fires_expense_split_assigned():
    import app.services.transaction_split_service as mod
    src = inspect.getsource(mod)
    assert "EXPENSE_SPLIT_ASSIGNED" in src


# ---------------------------------------------------------------------------
# 4. TransactionSplit model — settled_at column
# ---------------------------------------------------------------------------

def test_transaction_split_model_has_settled_at():
    from app.models.transaction import TransactionSplit
    assert hasattr(TransactionSplit, "settled_at")


def test_transaction_split_model_settled_at_is_nullable():
    from app.models.transaction import TransactionSplit
    col = TransactionSplit.__table__.c.get("settled_at")
    assert col is not None
    assert col.nullable is True


# ---------------------------------------------------------------------------
# 5. Schema — SettleRequest, SettleResponse, settled_at in response
# ---------------------------------------------------------------------------

def test_settle_request_schema_exists():
    from app.schemas.transaction_split import SettleRequest
    assert SettleRequest is not None


def test_settle_request_has_member_id_field():
    from app.schemas.transaction_split import SettleRequest
    fields = SettleRequest.model_fields
    assert "member_id" in fields


def test_settle_response_schema_exists():
    from app.schemas.transaction_split import SettleResponse
    assert SettleResponse is not None


def test_settle_response_has_settled_count():
    from app.schemas.transaction_split import SettleResponse
    fields = SettleResponse.model_fields
    assert "settled_count" in fields


def test_split_response_schema_has_settled_at():
    from app.schemas.transaction_split import TransactionSplitResponse
    fields = TransactionSplitResponse.model_fields
    assert "settled_at" in fields


# ---------------------------------------------------------------------------
# 6. API router — settle endpoint registered
# ---------------------------------------------------------------------------

def test_settle_endpoint_in_api_source():
    import app.api.v1.transaction_splits as mod
    src = inspect.getsource(mod)
    assert "/settle" in src
    assert "SettleRequest" in src
    assert "SettleResponse" in src


# ---------------------------------------------------------------------------
# 7. Migration r78_add_settled_at exists
# ---------------------------------------------------------------------------

def test_migration_r78_add_settled_at_exists():
    import importlib.util, pathlib
    migrations = pathlib.Path(__file__).parent.parent / "alembic" / "versions"
    found = any("r78_add_settled_at" in f.name for f in migrations.iterdir())
    assert found, "Migration r78_add_settled_at not found in alembic/versions/"


def test_migration_r78_revision_id():
    import importlib.util, pathlib
    migrations = pathlib.Path(__file__).parent.parent / "alembic" / "versions"
    target = next(f for f in migrations.iterdir() if "r78_add_settled_at" in f.name)
    spec = importlib.util.spec_from_file_location("mig", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.revision == "r78_add_settled_at"
    assert mod.down_revision == "r77_household_notif"


# ---------------------------------------------------------------------------
# 8. settle_member method fires SETTLEMENT_REMINDER
# ---------------------------------------------------------------------------

def test_transaction_split_service_fires_settlement_reminder():
    import app.services.transaction_split_service as mod
    src = inspect.getsource(mod)
    assert "SETTLEMENT_REMINDER" in src


def test_transaction_split_service_settle_member_method_exists():
    from app.services.transaction_split_service import TransactionSplitService
    assert hasattr(TransactionSplitService, "settle_member")
