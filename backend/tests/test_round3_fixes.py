"""Tests for round 3 fixes: input validation, task retry configs, and utc_now usage."""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# 1. transaction merchant_name too long → 422
# ---------------------------------------------------------------------------

def test_transaction_merchant_name_too_long_returns_422(
    client: TestClient, auth_headers, test_account
):
    """POST /transactions/ with 300-char merchant_name should return 422."""
    payload = {
        "account_id": str(test_account.id),
        "date": "2024-01-15",
        "amount": -50.00,
        "merchant_name": "A" * 300,
        "description": "Test",
    }
    response = client.post("/api/v1/transactions/", json=payload, headers=auth_headers)
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# 2. transaction notes too long → 422
# ---------------------------------------------------------------------------

def test_transaction_notes_too_long_returns_422(
    client: TestClient, auth_headers, test_account
):
    """POST /transactions/ with 15000-char notes should return 422."""
    payload = {
        "account_id": str(test_account.id),
        "date": "2024-01-15",
        "amount": -50.00,
        "merchant_name": "Shop",
        "notes": "N" * 15000,
    }
    response = client.post("/api/v1/transactions/", json=payload, headers=auth_headers)
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# 3. budget end_date before start_date → 422
# ---------------------------------------------------------------------------

def test_budget_end_date_before_start_date_returns_422(
    client: TestClient, auth_headers
):
    """POST /budgets with end_date < start_date should return 422."""
    payload = {
        "name": "Bad Budget",
        "amount": 500.00,
        "period": "MONTHLY",
        "start_date": "2024-06-01",
        "end_date": "2024-01-01",
    }
    response = client.post("/api/v1/budgets", json=payload, headers=auth_headers)
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# 4. report template with invalid type → 422
# ---------------------------------------------------------------------------

def test_report_template_invalid_type_returns_422(
    client: TestClient, auth_headers
):
    """POST /reports/templates with report_type='garbage' should return 422."""
    payload = {
        "name": "My Report",
        "report_type": "garbage",
        "config": {"dateRange": {"type": "preset", "preset": "last_30_days"}},
        "is_shared": False,
    }
    response = client.post("/api/v1/reports/templates", json=payload, headers=auth_headers)
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# 5. report_task uses utc_now, not date.today
# ---------------------------------------------------------------------------

def test_report_task_uses_utc_date():
    """send_scheduled_reports_task async helper must use utc_now().date(), not date.today()."""
    import inspect
    import app.workers.tasks.report_tasks as rt_module

    source = inspect.getsource(rt_module._send_scheduled_reports_async)
    assert "utc_now" in source, "_send_scheduled_reports_async must call utc_now()"
    assert "date.today()" not in source, "_send_scheduled_reports_async must not use date.today()"


# ---------------------------------------------------------------------------
# 6. retirement task has retry config
# ---------------------------------------------------------------------------

def test_retirement_task_has_retry_config():
    """run_retirement_simulation Celery task must have max_retries > 0."""
    from app.workers.tasks.retirement_tasks import run_retirement_simulation

    assert hasattr(run_retirement_simulation, "max_retries"), (
        "run_retirement_simulation must declare max_retries"
    )
    assert run_retirement_simulation.max_retries > 0, (
        "run_retirement_simulation.max_retries must be > 0"
    )


# ---------------------------------------------------------------------------
# 7. report task has retry config
# ---------------------------------------------------------------------------

def test_report_task_has_retry_config():
    """send_scheduled_reports_task Celery task must have max_retries > 0."""
    from app.workers.tasks.report_tasks import send_scheduled_reports_task

    assert hasattr(send_scheduled_reports_task, "max_retries"), (
        "send_scheduled_reports_task must declare max_retries"
    )
    assert send_scheduled_reports_task.max_retries > 0, (
        "send_scheduled_reports_task.max_retries must be > 0"
    )
