"""
PM Audit Round 76 — Household living-together fixes.

Changes covered:
1. MemberSettlementWidget registered in ADVANCED_LAYOUT (widgetRegistry.tsx)
2. is_split field added to Transaction schema response
3. Split badge shown in TransactionsPage (relies on is_split in schema)
4. DashboardSummary now includes spending_by_member list
5. Dashboard API imports TransactionSplit model for per-member query
6. Dashboard cache TTLs extracted to named module-level constants
7. DB migration r76_member_split adds assigned_user_id to transaction_splits
"""

import inspect


# ---------------------------------------------------------------------------
# 1. Transaction schema — is_split exposed in response
# ---------------------------------------------------------------------------

def test_transaction_response_schema_has_is_split():
    from app.schemas.transaction import Transaction as TransactionSchema
    fields = TransactionSchema.model_fields
    assert "is_split" in fields, "is_split must be in Transaction response schema"


def test_transaction_response_is_split_defaults_false():
    from app.schemas.transaction import Transaction as TransactionSchema
    field = TransactionSchema.model_fields["is_split"]
    # pydantic v2: default stored in field_info
    assert field.default is False or field.default == False  # noqa: E712


# ---------------------------------------------------------------------------
# 2. DashboardSummary — spending_by_member field
# ---------------------------------------------------------------------------

def test_dashboard_summary_has_spending_by_member():
    from app.api.v1.dashboard import DashboardSummary
    fields = DashboardSummary.model_fields
    assert "spending_by_member" in fields


def test_member_spending_model_exists():
    from app.api.v1.dashboard import MemberSpending
    fields = MemberSpending.model_fields
    assert "member_id" in fields
    assert "member_name" in fields
    assert "spending" in fields


def test_dashboard_summary_spending_by_member_defaults_empty():
    from app.api.v1.dashboard import DashboardSummary
    s = DashboardSummary(
        net_worth=0,
        total_assets=0,
        total_debts=0,
        monthly_spending=0,
        monthly_income=0,
        monthly_net=0,
    )
    assert s.spending_by_member == []


# ---------------------------------------------------------------------------
# 3. Dashboard API — imports TransactionSplit, computes per-member spending
# ---------------------------------------------------------------------------

def test_dashboard_api_imports_transaction_split():
    import app.api.v1.dashboard as mod
    src = inspect.getsource(mod)
    assert "TransactionSplit" in src


def test_dashboard_api_has_spending_by_member_logic():
    import app.api.v1.dashboard as mod
    src = inspect.getsource(mod)
    assert "spending_by_member" in src


def test_dashboard_api_queries_account_user_id():
    """Per-member breakdown groups by Account.user_id."""
    import app.api.v1.dashboard as mod
    src = inspect.getsource(mod)
    assert "Account.user_id" in src


# ---------------------------------------------------------------------------
# 4. Dashboard cache TTLs — named constants
# ---------------------------------------------------------------------------

def test_dashboard_cache_ttl_summary_constant_exists():
    from app.api.v1.dashboard import _CACHE_TTL_SUMMARY
    assert isinstance(_CACHE_TTL_SUMMARY, int)
    assert _CACHE_TTL_SUMMARY > 0


def test_dashboard_cache_ttl_dashboard_constant_exists():
    from app.api.v1.dashboard import _CACHE_TTL_DASHBOARD
    assert isinstance(_CACHE_TTL_DASHBOARD, int)
    assert _CACHE_TTL_DASHBOARD > 0


def test_dashboard_cache_ttl_health_constant_exists():
    from app.api.v1.dashboard import _CACHE_TTL_HEALTH
    assert isinstance(_CACHE_TTL_HEALTH, int)
    assert _CACHE_TTL_HEALTH > 0


def test_dashboard_no_bare_300_cache_calls():
    """All cache_setex calls must use named constants, not bare ints."""
    import app.api.v1.dashboard as mod
    src = inspect.getsource(mod)
    # The named constant definitions themselves contain '300' — exclude those
    lines_with_300 = [
        line for line in src.splitlines()
        if "cache_setex" in line and ", 300," in line
    ]
    assert lines_with_300 == [], f"Bare 300 TTL found: {lines_with_300}"


def test_dashboard_no_bare_3600_cache_calls():
    import app.api.v1.dashboard as mod
    src = inspect.getsource(mod)
    lines_with_3600 = [
        line for line in src.splitlines()
        if "cache_setex" in line and ", 3600," in line
    ]
    assert lines_with_3600 == [], f"Bare 3600 TTL found: {lines_with_3600}"


def test_dashboard_no_bare_60_cache_calls():
    import app.api.v1.dashboard as mod
    src = inspect.getsource(mod)
    lines_with_60 = [
        line for line in src.splitlines()
        if "cache_setex" in line and ", 60," in line
    ]
    assert lines_with_60 == [], f"Bare 60 TTL found: {lines_with_60}"


# ---------------------------------------------------------------------------
# 5. Migration r76_member_split exists and is well-formed
# ---------------------------------------------------------------------------

def test_r76_migration_file_exists():
    import importlib.util, pathlib
    migrations_dir = pathlib.Path(__file__).parents[1] / "alembic" / "versions"
    files = list(migrations_dir.glob("r76_*.py"))
    assert files, "r76 migration file not found"


def test_r76_migration_revision_id():
    import importlib.util, pathlib
    migrations_dir = pathlib.Path(__file__).parents[1] / "alembic" / "versions"
    files = list(migrations_dir.glob("r76_*.py"))
    assert files
    spec = importlib.util.spec_from_file_location("r76", files[0])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod.revision) <= 32, "Revision ID must fit in alembic_version VARCHAR(32)"


def test_r76_migration_adds_assigned_user_id():
    import importlib.util, pathlib, inspect
    migrations_dir = pathlib.Path(__file__).parents[1] / "alembic" / "versions"
    files = list(migrations_dir.glob("r76_*.py"))
    assert files
    spec = importlib.util.spec_from_file_location("r76", files[0])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    src = inspect.getsource(mod.upgrade)
    assert "assigned_user_id" in src
    assert "transaction_splits" in src


# ---------------------------------------------------------------------------
# 6. TransactionSplit model — assigned_user_id and relationship
# ---------------------------------------------------------------------------

def test_transaction_split_model_has_assigned_user_id():
    from app.models.transaction import TransactionSplit
    assert hasattr(TransactionSplit, "assigned_user_id")


def test_transaction_split_model_assigned_user_relationship():
    from app.models.transaction import TransactionSplit
    assert hasattr(TransactionSplit, "assigned_user")
