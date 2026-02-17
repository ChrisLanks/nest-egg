# Backend Testing Guide

This directory contains all tests for the Nest Egg backend API.

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and test configuration
├── unit/                 # Unit tests for services and utilities
│   ├── test_auth_service.py
│   ├── test_budget_service.py
│   └── ...
├── integration/          # Integration tests for database operations
│   └── ...
└── api/                  # API endpoint tests
    ├── test_auth_endpoints.py
    └── ...
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run specific test categories
```bash
# Unit tests only
pytest -m unit

# API tests only
pytest -m api

# Integration tests only
pytest -m integration

# Slow tests only
pytest -m slow
```

### Run tests for specific file
```bash
pytest tests/unit/test_auth_service.py
```

### Run specific test
```bash
pytest tests/unit/test_auth_service.py::TestAuthService::test_hash_password
```

### Run with verbose output
```bash
pytest -v
```

### Run with print statements visible
```bash
pytest -s
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (database, external services)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.auth` - Authentication-related tests
- `@pytest.mark.plaid` - Plaid integration tests
- `@pytest.mark.rules` - Rule engine tests

## Fixtures

### Database Fixtures
- `db_session` - Async database session for tests
- `test_engine` - Test database engine (in-memory SQLite)
- `override_get_db` - Override for FastAPI dependency

### User Fixtures
- `test_organization` - Test organization
- `test_user` - Test user with admin privileges
- `auth_headers` - Authentication headers with valid JWT token

### Client Fixtures
- `client` - Synchronous test client (FastAPI TestClient)
- `async_client` - Async test client (httpx AsyncClient)

### Sample Data Fixtures
- `sample_transaction_data` - Sample transaction payload
- `sample_budget_data` - Sample budget payload
- `sample_rule_data` - Sample rule payload

## Writing Tests

### Unit Test Example
```python
import pytest

@pytest.mark.unit
class TestMyService:
    def test_calculation(self):
        result = MyService.calculate(10, 20)
        assert result == 30
```

### API Test Example
```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.api
class TestMyEndpoint:
    def test_create_item(self, client: TestClient, auth_headers):
        response = client.post(
            "/api/v1/items",
            json={"name": "Test"},
            headers=auth_headers,
        )
        assert response.status_code == 201
```

### Async Test Example
```python
import pytest

@pytest.mark.asyncio
async def test_async_function(db_session):
    result = await my_async_function(db_session)
    assert result is not None
```

## Coverage Requirements

- **Minimum coverage:** 70%
- **Target coverage:** 80%+
- **Critical services:** 90%+ (auth, payment, budget calculations)

View coverage report:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

Tests run automatically on:
- Every push to `main`, `master`, or `develop` branches
- Every pull request

GitHub Actions workflow checks:
1. Code formatting (black, isort)
2. Linting (flake8, pylint)
3. Type checking (mypy)
4. All tests with coverage
5. Security scan (safety, trivy)

## Best Practices

### DO
- ✅ Use descriptive test names: `test_user_login_with_invalid_password`
- ✅ Test edge cases and error conditions
- ✅ Use fixtures for setup and teardown
- ✅ Keep tests independent (can run in any order)
- ✅ Test one thing per test function
- ✅ Use appropriate markers
- ✅ Mock external services (Plaid, email, etc.)

### DON'T
- ❌ Test framework code (FastAPI, SQLAlchemy)
- ❌ Make tests depend on each other
- ❌ Use production database for tests
- ❌ Hardcode sensitive data
- ❌ Skip writing tests for new code
- ❌ Make API calls to real services in tests

## Test Data Best Practices

### Use Factories
For complex test data, consider using factories:
```python
def create_test_transaction(db_session, **kwargs):
    defaults = {
        "amount": -50.00,
        "merchant_name": "Test Merchant",
        "date": date.today(),
    }
    defaults.update(kwargs)
    transaction = Transaction(**defaults)
    db_session.add(transaction)
    await db_session.commit()
    return transaction
```

### Clean Up After Tests
Tests use in-memory database that's reset after each test, but if you create external resources:
```python
@pytest.fixture
async def test_file():
    file_path = "/tmp/test.csv"
    with open(file_path, "w") as f:
        f.write("test data")
    yield file_path
    os.remove(file_path)  # Cleanup
```

## Troubleshooting

### Tests failing locally but passing in CI
- Check Python version matches CI (3.11)
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Clear pytest cache: `pytest --cache-clear`

### Database errors
- Check test database URL in conftest.py
- Ensure migrations are applied
- Reset database: Drop and recreate test DB

### Slow tests
- Use `-m "not slow"` to skip slow tests during development
- Consider mocking external APIs
- Use smaller datasets for tests

## Adding New Tests

1. Determine test category (unit/integration/api)
2. Create test file in appropriate directory
3. Add appropriate markers
4. Write test using fixtures
5. Verify test passes: `pytest path/to/test_file.py`
6. Check coverage: `pytest --cov=app path/to/test_file.py`

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
