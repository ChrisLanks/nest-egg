"""
PM Audit Round 80 — Production hardening: rate limits + query bounds + DB indexes.

Changes covered:
1. smart_insights.py: rate limiting added to get_smart_insights (30/min),
   get_roth_conversion (10/min — CPU heavy), get_fund_fees (20/min)
2. smart_insights.py: fund-fees holdings query bounded with .limit(10_000)
3. notification.py: composite index ix_notifications_user_unread_created
   (user_id, is_read, created_at) for unread-notifications dashboard query
4. Migration r79_notif_covering_idx creates the index
"""

import inspect


# ---------------------------------------------------------------------------
# 1. smart_insights.py — rate_limit_service imported
# ---------------------------------------------------------------------------

def test_smart_insights_imports_rate_limit_service():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod)
    assert "rate_limit_service" in src


def test_smart_insights_imports_request():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod)
    assert "Request" in src


# ---------------------------------------------------------------------------
# 2. get_smart_insights — has rate limit call
# ---------------------------------------------------------------------------

def test_get_smart_insights_has_rate_limit():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod.get_smart_insights)
    assert "check_rate_limit" in src


def test_get_smart_insights_rate_limit_max_30():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod.get_smart_insights)
    assert "max_requests=30" in src


# ---------------------------------------------------------------------------
# 3. get_roth_conversion — has tight rate limit (CPU-heavy)
# ---------------------------------------------------------------------------

def test_get_roth_conversion_has_rate_limit():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod.get_roth_conversion)
    assert "check_rate_limit" in src


def test_get_roth_conversion_rate_limit_max_10():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod.get_roth_conversion)
    assert "max_requests=10" in src


# ---------------------------------------------------------------------------
# 4. get_fund_fees — has rate limit and bounded query
# ---------------------------------------------------------------------------

def test_get_fund_fees_has_rate_limit():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod.get_fund_fees)
    assert "check_rate_limit" in src


def test_get_fund_fees_rate_limit_max_20():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod.get_fund_fees)
    assert "max_requests=20" in src


def test_get_fund_fees_holdings_query_has_limit():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod.get_fund_fees)
    assert ".limit(" in src


# ---------------------------------------------------------------------------
# 5. notification.py — composite covering index present in __table_args__
# ---------------------------------------------------------------------------

def test_notification_covering_index_in_model():
    from app.models.notification import Notification
    index_names = [idx.name for idx in Notification.__table__.indexes]
    assert "ix_notifications_user_unread_created" in index_names


def test_notification_covering_index_columns():
    from app.models.notification import Notification
    idx = next(
        i for i in Notification.__table__.indexes
        if i.name == "ix_notifications_user_unread_created"
    )
    col_names = [c.name for c in idx.columns]
    assert col_names == ["user_id", "is_read", "created_at"]


# ---------------------------------------------------------------------------
# 6. Migration r79_notif_covering_idx exists and chains correctly
# ---------------------------------------------------------------------------

def test_migration_r79_exists():
    import pathlib
    migrations = pathlib.Path(__file__).parent.parent / "alembic" / "versions"
    found = any("r79_notification_covering_index" in f.name for f in migrations.iterdir())
    assert found, "Migration r79_notification_covering_index not found"


def test_migration_r79_revision_and_chain():
    import importlib.util, pathlib
    migrations = pathlib.Path(__file__).parent.parent / "alembic" / "versions"
    target = next(f for f in migrations.iterdir() if "r79_notification_covering_index" in f.name)
    spec = importlib.util.spec_from_file_location("mig_r79", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.revision == "r79_notif_covering_idx"
    assert mod.down_revision == "r78_add_settled_at"
