"""Tests for Celery async session utility and task migrations.

Verifies that:
- get_celery_session() creates a NullPool engine (no stale event loop)
- get_celery_session() properly disposes the engine on exit
- All Celery tasks use get_celery_session instead of module-level AsyncSessionLocal
- The auth token cleanup task uses func.now() (server-side, no timezone mismatch)
- The holdings price task uses utc_now() (naive, no timezone mismatch)
"""

import ast
import importlib
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetCelerySession:
    """Tests for the get_celery_session utility."""

    def test_get_celery_session_is_async_context_manager(self):
        """get_celery_session should be an async context manager."""
        from app.workers.utils import get_celery_session

        result = get_celery_session()
        assert hasattr(result, "__aenter__")
        assert hasattr(result, "__aexit__")

    @pytest.mark.asyncio
    async def test_get_celery_session_creates_nullpool_engine(self):
        """get_celery_session should use NullPool to avoid stale connections."""
        from sqlalchemy.pool import NullPool

        from app.workers.utils import get_celery_session

        with patch("app.workers.utils.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.close = AsyncMock()
            mock_engine.dispose = AsyncMock()

            mock_factory = MagicMock(return_value=mock_session)
            mock_create.return_value = mock_engine

            with patch("app.workers.utils.async_sessionmaker", return_value=mock_factory):
                async with get_celery_session() as _session:
                    pass

            # Verify NullPool was specified
            call_kwargs = mock_create.call_args
            assert call_kwargs.kwargs.get("poolclass") is NullPool

    @pytest.mark.asyncio
    async def test_get_celery_session_disposes_engine(self):
        """Engine should be disposed after the context manager exits."""
        from app.workers.utils import get_celery_session

        with patch("app.workers.utils.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.close = AsyncMock()
            mock_engine.dispose = AsyncMock()

            mock_factory = MagicMock(return_value=mock_session)
            mock_create.return_value = mock_engine

            with patch("app.workers.utils.async_sessionmaker", return_value=mock_factory):
                async with get_celery_session() as _session:
                    pass

            mock_engine.dispose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_celery_session_sets_application_name(self):
        """Engine should use 'nest_egg_celery' application name."""
        from app.workers.utils import get_celery_session

        with patch("app.workers.utils.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.close = AsyncMock()
            mock_engine.dispose = AsyncMock()

            mock_factory = MagicMock(return_value=mock_session)
            mock_create.return_value = mock_engine

            with patch("app.workers.utils.async_sessionmaker", return_value=mock_factory):
                async with get_celery_session() as _session:
                    pass

            connect_args = mock_create.call_args.kwargs.get("connect_args", {})
            app_name = connect_args.get("server_settings", {}).get("application_name")
            assert app_name == "nest_egg_celery"

    @pytest.mark.asyncio
    async def test_get_celery_session_disposes_engine_on_error(self):
        """Engine should be disposed even when an exception occurs."""
        from app.workers.utils import get_celery_session

        with patch("app.workers.utils.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.close = AsyncMock()
            mock_engine.dispose = AsyncMock()

            mock_factory = MagicMock(return_value=mock_session)
            mock_create.return_value = mock_engine

            with patch("app.workers.utils.async_sessionmaker", return_value=mock_factory):
                with pytest.raises(ValueError, match="test error"):
                    async with get_celery_session() as _session:
                        raise ValueError("test error")

            mock_engine.dispose.assert_awaited_once()


class TestAllTasksUseCelerySession:
    """Verify all Celery task files use get_celery_session, not AsyncSessionLocal."""

    TASK_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "workers" / "tasks"

    def _get_task_files(self):
        """Get all Python task files."""
        return [f for f in self.TASK_DIR.glob("*.py") if f.name != "__init__.py"]

    def test_no_task_imports_async_session_local(self):
        """No task file should import AsyncSessionLocal from database."""
        for task_file in self._get_task_files():
            source = task_file.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "database" in node.module:
                        names = [alias.name for alias in node.names]
                        assert (
                            "AsyncSessionLocal" not in names
                        ), f"{task_file.name} still imports AsyncSessionLocal"

    def test_no_task_uses_async_session_factory_alias(self):
        """No task file should reference async_session_factory."""
        for task_file in self._get_task_files():
            source = task_file.read_text()
            assert (
                "async_session_factory" not in source
            ), f"{task_file.name} still references async_session_factory"

    def test_all_async_tasks_use_get_celery_session(self):
        """Every async task function should use get_celery_session."""
        for task_file in self._get_task_files():
            source = task_file.read_text()
            # If the file has asyncio.run (meaning it has async task logic),
            # it should reference get_celery_session
            if "asyncio.run(" in source:
                assert (
                    "get_celery_session" in source
                ), f"{task_file.name} uses asyncio.run but not get_celery_session"


class TestAuthTaskTimezonefix:
    """Verify the auth task uses server-side func.now() instead of Python datetime."""

    def test_auth_task_uses_func_now(self):
        """cleanup should use func.now() not datetime.now()."""
        source = inspect.getsource(importlib.import_module("app.workers.tasks.auth_tasks"))
        assert "func.now()" in source
        assert "datetime.now" not in source
        assert "timezone.utc" not in source

    def test_auth_task_does_not_import_datetime(self):
        """auth_tasks should not import datetime at all."""
        source = inspect.getsource(importlib.import_module("app.workers.tasks.auth_tasks"))
        assert "from datetime" not in source
        assert "import datetime" not in source


class TestHoldingsTaskTimezoneFix:
    """Verify holdings price update uses naive utc_now() instead of aware datetime."""

    def test_holdings_price_update_uses_utc_now(self):
        """update_holdings_prices should use utc_now() not datetime.now(timezone.utc)."""
        source = inspect.getsource(importlib.import_module("app.workers.tasks.holdings_tasks"))
        # Should use utc_now() (naive, compatible with TIMESTAMP WITHOUT TIME ZONE)
        assert "utc_now()" in source
        # Should NOT use timezone-aware datetime.now(timezone.utc)
        assert "datetime.now(timezone.utc)" not in source

    def test_holdings_does_not_import_datetime_timezone(self):
        """holdings_tasks should not import datetime or timezone."""
        from app.workers.tasks import holdings_tasks

        source = inspect.getsource(holdings_tasks)
        assert "from datetime import datetime" not in source
        assert "timezone" not in source


class TestTaskImportsValid:
    """Smoke-test that all task modules can be imported without errors."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "app.workers.tasks.auth_tasks",
            "app.workers.tasks.budget_tasks",
            "app.workers.tasks.recurring_tasks",
            "app.workers.tasks.forecast_tasks",
            "app.workers.tasks.retention_tasks",
            "app.workers.tasks.holdings_tasks",
            "app.workers.tasks.interest_accrual_tasks",
            "app.workers.tasks.snapshot_tasks",
            "app.workers.tasks.retirement_tasks",
        ],
    )
    def test_task_module_imports(self, module_name):
        """Each task module should import without errors."""
        mod = importlib.import_module(module_name)
        assert mod is not None
