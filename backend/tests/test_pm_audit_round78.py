"""
PM Audit Round 78 — Hardcoded constant cleanup + household notifications.

Changes covered:
1. bond_ladder_service.py: base_rate fallback uses FIRE.DEFAULT_WITHDRAWAL_RATE
2. holdings.py: fee-drag annual_return uses FIRE.DEFAULT_EXPECTED_RETURN
3. NotificationType enum adds expense_split_assigned + settlement_reminder
4. Migration r77_household_notif adds enum values to DB
"""

import inspect


# ---------------------------------------------------------------------------
# 1. bond_ladder_service — no bare 0.04 fallback
# ---------------------------------------------------------------------------

def test_bond_ladder_service_imports_fire():
    import app.services.bond_ladder_service as mod
    src = inspect.getsource(mod)
    assert "from app.constants.financial import FIRE" in src


def test_bond_ladder_service_no_bare_0_04_fallback():
    import app.services.bond_ladder_service as mod
    src = inspect.getsource(mod)
    # The fallback should reference the FIRE constant, not a bare float literal
    assert "base_rate = 0.04" not in src


def test_bond_ladder_service_fallback_uses_fire_constant():
    import app.services.bond_ladder_service as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_WITHDRAWAL_RATE" in src


# ---------------------------------------------------------------------------
# 2. holdings.py — fee drag uses FIRE.DEFAULT_EXPECTED_RETURN
# ---------------------------------------------------------------------------

def test_holdings_api_imports_fire():
    import app.api.v1.holdings as mod
    src = inspect.getsource(mod)
    assert "from app.constants.financial import FIRE" in src


def test_holdings_api_no_bare_0_07_annual_return():
    import app.api.v1.holdings as mod
    src = inspect.getsource(mod)
    # The fee-drag function must not contain a bare literal assignment
    assert "annual_return = 0.07" not in src


def test_holdings_api_fee_drag_uses_fire_constant():
    import app.api.v1.holdings as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_EXPECTED_RETURN" in src


# ---------------------------------------------------------------------------
# 3. NotificationType — new household expense-split values
# ---------------------------------------------------------------------------

def test_notification_type_has_expense_split_assigned():
    from app.models.notification import NotificationType
    assert hasattr(NotificationType, "EXPENSE_SPLIT_ASSIGNED")
    assert NotificationType.EXPENSE_SPLIT_ASSIGNED.value == "expense_split_assigned"


def test_notification_type_has_settlement_reminder():
    from app.models.notification import NotificationType
    assert hasattr(NotificationType, "SETTLEMENT_REMINDER")
    assert NotificationType.SETTLEMENT_REMINDER.value == "settlement_reminder"


# ---------------------------------------------------------------------------
# 4. Migration r77 exists and is well-formed
# ---------------------------------------------------------------------------

def test_r77_migration_file_exists():
    import pathlib
    migrations_dir = pathlib.Path(__file__).parents[1] / "alembic" / "versions"
    files = list(migrations_dir.glob("r77_*.py"))
    assert files, "r77 migration file not found"


def test_r77_migration_revision_fits_varchar32():
    import importlib.util, pathlib
    migrations_dir = pathlib.Path(__file__).parents[1] / "alembic" / "versions"
    files = list(migrations_dir.glob("r77_*.py"))
    assert files
    spec = importlib.util.spec_from_file_location("r77", files[0])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod.revision) <= 32


def test_r77_migration_adds_expense_split_assigned():
    import importlib.util, pathlib, inspect
    migrations_dir = pathlib.Path(__file__).parents[1] / "alembic" / "versions"
    files = list(migrations_dir.glob("r77_*.py"))
    assert files
    spec = importlib.util.spec_from_file_location("r77", files[0])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    src = inspect.getsource(mod.upgrade)
    assert "expense_split_assigned" in src


def test_r77_migration_adds_settlement_reminder():
    import importlib.util, pathlib, inspect
    migrations_dir = pathlib.Path(__file__).parents[1] / "alembic" / "versions"
    files = list(migrations_dir.glob("r77_*.py"))
    assert files
    spec = importlib.util.spec_from_file_location("r77", files[0])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    src = inspect.getsource(mod.upgrade)
    assert "settlement_reminder" in src


# ---------------------------------------------------------------------------
# 5. FIRE constants referenced are present
# ---------------------------------------------------------------------------

def test_fire_default_withdrawal_rate_exists():
    from app.constants.financial import FIRE
    assert hasattr(FIRE, "DEFAULT_WITHDRAWAL_RATE")
    assert float(FIRE.DEFAULT_WITHDRAWAL_RATE) > 0


def test_fire_default_expected_return_exists():
    from app.constants.financial import FIRE
    assert hasattr(FIRE, "DEFAULT_EXPECTED_RETURN")
    assert float(FIRE.DEFAULT_EXPECTED_RETURN) > 0
