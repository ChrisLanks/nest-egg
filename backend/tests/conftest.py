"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User, Organization
from app.core.security import hash_password, create_access_token

# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def override_get_db(db_session: AsyncSession):
    """Override the get_db dependency."""

    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture(scope="function")
def client(override_get_db) -> TestClient:
    """Create a test client."""
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        id=uuid4(),
        name="Test Organization",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_organization: Organization) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        organization_id=test_organization.id,
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers with access token."""
    access_token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_transaction_data() -> dict:
    """Sample transaction data for testing."""
    return {
        "date": "2024-02-15",
        "amount": -50.00,
        "merchant_name": "Test Merchant",
        "description": "Test transaction",
        "category_primary": "Dining",
        "is_pending": False,
    }


@pytest.fixture
def sample_budget_data() -> dict:
    """Sample budget data for testing."""
    return {
        "name": "Groceries Budget",
        "category": "Groceries",
        "amount": 500.00,
        "period": "MONTHLY",
        "alert_threshold": 0.80,
        "is_active": True,
    }


@pytest.fixture
def sample_rule_data() -> dict:
    """Sample rule data for testing."""
    return {
        "name": "Auto-categorize Coffee",
        "is_active": True,
        "priority": 1,
        "match_type": "ALL",
        "apply_to": "NEW_ONLY",
        "conditions": [
            {
                "field": "MERCHANT_NAME",
                "operator": "CONTAINS",
                "value": "starbucks",
            }
        ],
        "actions": [
            {
                "action_type": "SET_CATEGORY",
                "action_value": "Coffee & Tea",
            }
        ],
    }
