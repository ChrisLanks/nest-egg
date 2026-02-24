"""Pytest configuration and shared fixtures."""

# IMPORTANT: Monkey-patch UUID support for SQLite BEFORE importing any models
import sys
from sqlalchemy import TypeDecorator, String, event
from sqlalchemy.engine import Engine
from sqlalchemy.dialects import postgresql as pg_dialect
import uuid as uuid_module

# Create SQLite-compatible UUID type
class SQLiteUUID(TypeDecorator):
    """Platform-independent UUID type for tests."""
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(String(36))
        return dialect.type_descriptor(pg_dialect.UUID(as_uuid=True))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid_module.UUID):
            return str(value) if dialect.name == 'sqlite' else value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid_module.UUID):
            return value
        return uuid_module.UUID(value)

# Replace PostgreSQL UUID with our SQLite-compatible version
pg_dialect.UUID = SQLiteUUID

# Also handle JSONB for SQLite
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON

class SQLiteJSONB(TypeDecorator):
    """Platform-independent JSONB type for tests."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(JSON())
        return dialect.type_descriptor(JSONB())

pg_dialect.JSONB = SQLiteJSONB

import asyncio
from decimal import Decimal
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
# Enable CSRF bypass for the test suite — this flag is the only authorised way
# to do this; it is explicitly checked in the middleware so that a mis-set
# ENVIRONMENT=test in a real deployment cannot disable CSRF protection.
settings.SKIP_CSRF_IN_TESTS = True

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User, Organization
from app.core.security import hash_password, create_access_token

# Test database URL — use StaticPool so in-memory SQLite shares one connection
# (NullPool creates a new connection per call, losing all tables each time)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign keys for SQLite."""
    if hasattr(dbapi_conn, 'execute'):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    # Import all models to ensure they're registered with Base.metadata
    from app.models import (  # noqa: F401
        user,
        account,
        transaction,
        budget,
        savings_goal,
        rule,
        holding,
        contribution,
        mfa,
        notification,
        portfolio_snapshot,
        recurring_transaction,
        report_template,
        transaction_merge,
        identity,
        permission,
        target_allocation,
        account_migration,
    )

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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


@pytest_asyncio.fixture(scope="function")
async def db(db_session: AsyncSession) -> AsyncSession:
    """Alias for db_session to match test function signatures."""
    return db_session


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
    async with AsyncClient(app=app, base_url="http://test", follow_redirects=True) as ac:
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
        password_hash=hash_password("password123"),
        organization_id=test_organization.id,
        is_org_admin=True,
        is_active=True,
        first_name="Test",
        last_name="User",
        failed_login_attempts=0,
        locked_until=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_account(db_session: AsyncSession, test_user: User):
    """Create a test account."""
    from app.models.account import Account, AccountType

    account = Account(
        id=uuid4(),
        organization_id=test_user.organization_id,
        user_id=test_user.id,
        name="Test Checking Account",
        account_type=AccountType.CHECKING,
        current_balance=Decimal("1000.00"),
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest_asyncio.fixture
async def second_organization(db_session: AsyncSession) -> Organization:
    """Create a second test organization for cross-org isolation tests."""
    org = Organization(
        id=uuid4(),
        name="Other Organization",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession, second_organization: Organization) -> User:
    """Create a second test user in a different organization for isolation tests."""
    user = User(
        id=uuid4(),
        email="other@example.com",
        password_hash=hash_password("password123"),
        organization_id=second_organization.id,
        is_org_admin=False,
        is_active=True,
        first_name="Other",
        last_name="User",
        failed_login_attempts=0,
        locked_until=None,
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


@pytest_asyncio.fixture
async def test_user_with_tokens(db_session: AsyncSession, test_user: User) -> tuple[str, str]:
    """Create test user with access and refresh tokens stored in database."""
    from app.core.security import create_refresh_token
    import hashlib
    from app.crud.user import refresh_token_crud

    # Generate tokens
    access_token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email})
    refresh_token_str, jti, expires_at = create_refresh_token(str(test_user.id))

    # Store refresh token hash
    token_hash = hashlib.sha256(jti.encode()).hexdigest()
    await refresh_token_crud.create(
        db=db_session,
        user_id=test_user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    return (access_token, refresh_token_str)


@pytest_asyncio.fixture
async def authenticated_client(override_get_db, test_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with authentication."""
    from app.dependencies import get_current_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    async with AsyncClient(app=app, base_url="http://test", follow_redirects=True) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def user_crud():
    """Provide user CRUD service."""
    from app.crud.user import user_crud as _user_crud
    return _user_crud


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
        "match_type": "all",
        "apply_to": "new_only",
        "conditions": [
            {
                "field": "merchant_name",
                "operator": "contains",
                "value": "starbucks",
            }
        ],
        "actions": [
            {
                "action_type": "set_category",
                "action_value": "Coffee & Tea",
            }
        ],
    }
