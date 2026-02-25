"""Tests for retirement planning API endpoints.

Verifies route registration, auth, and basic CRUD operations.
"""

import pytest
import pytest_asyncio
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.user import User


@pytest.mark.asyncio
async def test_create_default_scenario_route_exists(authenticated_client: AsyncClient):
    """POST /api/v1/retirement/scenarios/default must NOT return 404.

    This validates that the static /scenarios/default route is correctly
    registered and not shadowed by the parameterized /scenarios/{scenario_id}
    route.
    """
    response = await authenticated_client.post("/api/v1/retirement/scenarios/default")
    # Without a birthdate on the test user, we get 400 — but NOT 404.
    assert response.status_code != 404, (
        f"Route /scenarios/default returned 404 — likely shadowed by "
        f"/scenarios/{{scenario_id}}. Got: {response.json()}"
    )
    # Specifically expect 400 (no birthdate on default test_user)
    assert response.status_code == 400
    assert "birthdate" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_scenarios_returns_empty(authenticated_client: AsyncClient):
    """GET /api/v1/retirement/scenarios returns empty list when no scenarios exist."""
    response = await authenticated_client.get("/api/v1/retirement/scenarios")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_default_scenario_with_birthdate(
    authenticated_client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """POST /api/v1/retirement/scenarios/default creates a scenario when birthdate is set."""
    # Set birthdate on the test user
    test_user.birthdate = date(1990, 6, 15)
    db_session.add(test_user)
    await db_session.flush()

    response = await authenticated_client.post("/api/v1/retirement/scenarios/default")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"

    data = response.json()
    assert data["name"] == "My Retirement Plan"
    assert data["is_default"] is True
    assert data["retirement_age"] == 67
    assert data["life_expectancy"] == 95


@pytest.mark.asyncio
async def test_get_scenario_by_id(
    authenticated_client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """GET /api/v1/retirement/scenarios/{id} returns the correct scenario."""
    test_user.birthdate = date(1990, 6, 15)
    db_session.add(test_user)
    await db_session.flush()

    # Create a scenario first
    create_resp = await authenticated_client.post("/api/v1/retirement/scenarios/default")
    assert create_resp.status_code == 201
    scenario_id = create_resp.json()["id"]

    # Fetch it
    get_resp = await authenticated_client.get(f"/api/v1/retirement/scenarios/{scenario_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == scenario_id


@pytest.mark.asyncio
async def test_scenario_persists_across_requests(
    authenticated_client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Scenarios created via POST must be fetchable in a subsequent GET.

    Regression test: endpoints must call db.commit() so data survives
    beyond the request's session lifetime.
    """
    test_user.birthdate = date(1990, 6, 15)
    db_session.add(test_user)
    await db_session.flush()

    # Create
    create_resp = await authenticated_client.post("/api/v1/retirement/scenarios/default")
    assert create_resp.status_code == 201
    scenario_id = create_resp.json()["id"]

    # List — the new scenario must appear
    list_resp = await authenticated_client.get("/api/v1/retirement/scenarios")
    assert list_resp.status_code == 200
    ids = [s["id"] for s in list_resp.json()]
    assert scenario_id in ids, (
        f"Created scenario {scenario_id} not found in list. "
        "Endpoint likely missing db.commit()."
    )

    # Direct GET — must return 200, not 404
    get_resp = await authenticated_client.get(f"/api/v1/retirement/scenarios/{scenario_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == scenario_id


@pytest.mark.asyncio
async def test_get_nonexistent_scenario_returns_404(
    authenticated_client: AsyncClient,
):
    """GET for a random UUID must return 404, not 500."""
    fake_id = str(uuid4())
    resp = await authenticated_client.get(f"/api/v1/retirement/scenarios/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_quick_simulate_route(authenticated_client: AsyncClient):
    """POST /api/v1/retirement/quick-simulate runs a lightweight simulation."""
    payload = {
        "current_portfolio": 500000,
        "annual_contributions": 20000,
        "current_age": 35,
        "retirement_age": 65,
        "life_expectancy": 95,
        "annual_spending": 60000,
    }
    response = await authenticated_client.post("/api/v1/retirement/quick-simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "success_rate" in data
    assert "readiness_score" in data
    assert "projections" in data


@pytest.mark.asyncio
async def test_account_data_route(authenticated_client: AsyncClient):
    """GET /api/v1/retirement/account-data returns portfolio breakdown."""
    response = await authenticated_client.get("/api/v1/retirement/account-data")
    assert response.status_code == 200
    data = response.json()
    assert "total_portfolio" in data
    assert "taxable_balance" in data
    assert "annual_income" in data


@pytest.mark.asyncio
async def test_life_event_presets_route(authenticated_client: AsyncClient):
    """GET /api/v1/retirement/life-event-presets returns available presets."""
    response = await authenticated_client.get("/api/v1/retirement/life-event-presets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Check first preset has required fields
    preset = data[0]
    assert "key" in preset
    assert "name" in preset
    assert "category" in preset
