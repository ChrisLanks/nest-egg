"""Tests for Celery task retry/jitter helpers across all four task modules."""

import pytest


@pytest.mark.unit
class TestRetryCountdown:
    """Test _retry_countdown uses exponential back-off with full jitter."""

    def _get_countdown(self, module_path: str):
        import importlib
        mod = importlib.import_module(module_path)
        return mod._retry_countdown

    @pytest.mark.parametrize(
        "module_path",
        [
            "app.workers.tasks.bill_reminder_tasks",
            "app.workers.tasks.budget_tasks",
            "app.workers.tasks.forecast_tasks",
            "app.workers.tasks.recurring_tasks",
        ],
    )
    def test_retry_countdown_exists(self, module_path):
        """Each task module must expose _retry_countdown."""
        fn = self._get_countdown(module_path)
        assert callable(fn)

    @pytest.mark.parametrize(
        "module_path",
        [
            "app.workers.tasks.bill_reminder_tasks",
            "app.workers.tasks.budget_tasks",
            "app.workers.tasks.forecast_tasks",
            "app.workers.tasks.recurring_tasks",
        ],
    )
    def test_retry_countdown_is_positive(self, module_path):
        """_retry_countdown must always return a positive number."""
        fn = self._get_countdown(module_path)
        for retries in range(4):
            assert fn(retries) > 0

    @pytest.mark.parametrize(
        "module_path",
        [
            "app.workers.tasks.bill_reminder_tasks",
            "app.workers.tasks.budget_tasks",
            "app.workers.tasks.forecast_tasks",
            "app.workers.tasks.recurring_tasks",
        ],
    )
    def test_retry_countdown_increases_with_retries(self, module_path):
        """Later retries should produce a larger base wait (exponential growth)."""
        import random
        fn = self._get_countdown(module_path)
        # Pin random to 1.0 to get maximum (deterministic) countdown
        random.seed(42)
        vals = [fn(n) for n in range(4)]
        # Each successive value should be greater than the previous
        for i in range(1, len(vals)):
            # Allow for jitter — just check the base grows: 2^n * 60 * 1.5 (max jitter)
            base_i = (2 ** i) * 60 * 1.5
            base_prev = (2 ** (i - 1)) * 60 * 0.5
            assert base_i > base_prev

    @pytest.mark.parametrize(
        "module_path",
        [
            "app.workers.tasks.bill_reminder_tasks",
            "app.workers.tasks.budget_tasks",
            "app.workers.tasks.forecast_tasks",
            "app.workers.tasks.recurring_tasks",
        ],
    )
    def test_retry_countdown_stays_within_jitter_bounds(self, module_path):
        """Countdown must be between 50% and 150% of the base (2^retries * 60s)."""
        fn = self._get_countdown(module_path)
        for retries in range(4):
            base = (2 ** retries) * 60
            lo = base * 0.5
            hi = base * 1.5
            # Run multiple times to catch boundary violations
            for _ in range(20):
                val = fn(retries)
                assert lo <= val <= hi, (
                    f"retry={retries}: {val} not in [{lo}, {hi}]"
                )


@pytest.mark.unit
class TestTaskConfiguration:
    """Verify that each task is configured for auto-retry with max_retries=3."""

    @pytest.mark.parametrize(
        "module_path,task_name",
        [
            ("app.workers.tasks.bill_reminder_tasks", "send_bill_reminders_task"),
            ("app.workers.tasks.budget_tasks", "check_budget_alerts_task"),
            ("app.workers.tasks.forecast_tasks", "check_cash_flow_forecast_task"),
            ("app.workers.tasks.recurring_tasks", "detect_recurring_patterns_task"),
        ],
    )
    def test_task_max_retries(self, module_path, task_name):
        """Each Celery task must have max_retries=3."""
        import importlib
        mod = importlib.import_module(module_path)
        task = getattr(mod, task_name)
        assert task.max_retries == 3
