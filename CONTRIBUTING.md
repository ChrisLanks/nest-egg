# Contributing to Nest Egg

Thank you for contributing to Nest Egg! This guide will help you get started.

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- Git

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/nest-egg.git
   cd nest-egg
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

4. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

## Development Workflow

### Before You Start Coding

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Pull latest changes**
   ```bash
   git pull origin main
   ```

### While Coding

1. **Run tests frequently**
   ```bash
   cd backend
   make test
   ```

2. **Check code formatting**
   ```bash
   make lint
   ```

3. **Auto-format code**
   ```bash
   make format
   ```

### Before Committing

Pre-commit hooks will automatically:
- Format code with Black
- Sort imports with isort
- Check for trailing whitespace
- Validate YAML/JSON files
- Check for secrets

If hooks fail, fix the issues and try again.

### Commit Message Guidelines

Use conventional commits format:
```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(auth): add multi-factor authentication
fix(budget): correct threshold calculation
docs(api): update authentication endpoints
test(rules): add rule engine unit tests
```

### Creating a Pull Request

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub**
   - Use descriptive title
   - Fill out PR template
   - Link related issues
   - Add screenshots for UI changes

3. **Wait for CI checks**
   - All tests must pass
   - Coverage must be ≥70%
   - Code must be formatted
   - No linting errors

4. **Address review feedback**
   - Make requested changes
   - Push updates to same branch
   - Respond to comments

## Code Standards

### Python (Backend)

**Style Guide:**
- Follow PEP 8
- Line length: 100 characters
- Use type hints
- Write docstrings for public functions

**Example:**
```python
from typing import List, Optional
from decimal import Decimal

async def calculate_budget_progress(
    budget_id: str,
    period: str,
    user_id: Optional[str] = None
) -> Decimal:
    """
    Calculate budget progress for a given period.

    Args:
        budget_id: Budget identifier
        period: Time period (MONTHLY, QUARTERLY, YEARLY)
        user_id: Optional user filter

    Returns:
        Decimal representing budget utilization percentage

    Raises:
        ValueError: If budget not found
    """
    # Implementation here
    pass
```

**Testing:**
- Write tests for all new code
- Minimum 70% coverage for new code
- Use appropriate markers (`@pytest.mark.unit`, etc.)
- Mock external services (Plaid, email)

**Database Migrations:**
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Review generated migration
# Edit if needed

# Apply migration
alembic upgrade head

# Test downgrade
alembic downgrade -1
alembic upgrade head
```

### TypeScript (Frontend)

**Style Guide:**
- Use TypeScript (not JavaScript)
- Follow ESLint rules
- Use functional components with hooks
- Prefer const over let

**Example:**
```typescript
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

interface Transaction {
  id: string;
  amount: number;
  merchant_name: string;
}

export const TransactionList: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['transactions'],
    queryFn: async () => {
      const response = await api.get<Transaction[]>('/transactions');
      return response.data;
    },
  });

  if (isLoading) return <Spinner />;

  return (
    <div>
      {data?.map(tx => (
        <div key={tx.id}>{tx.merchant_name}</div>
      ))}
    </div>
  );
};
```

## Testing Guidelines

### Unit Tests (Backend)

**Location:** `backend/tests/unit/`

**What to test:**
- Service methods
- Utility functions
- Business logic
- Calculations

**Example:**
```python
@pytest.mark.unit
class TestBudgetService:
    def test_calculate_progress(self):
        spent = Decimal("300.00")
        budget = Decimal("500.00")

        result = BudgetService._calculate_progress(spent, budget)

        assert result["percentage"] == 60.0
```

### API Tests (Backend)

**Location:** `backend/tests/api/`

**What to test:**
- Endpoint responses
- Status codes
- Request/response schemas
- Authentication
- Error handling

**Example:**
```python
@pytest.mark.api
def test_create_budget(client, auth_headers):
    response = client.post(
        "/api/v1/budgets",
        json={"name": "Groceries", "amount": 500},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Groceries"
```

### Frontend Tests

**Location:** `frontend/src/__tests__/`

Use React Testing Library for component tests.

## Security Guidelines

### DO
- ✅ Validate all user input
- ✅ Use parameterized queries (SQLAlchemy ORM)
- ✅ Hash passwords with Argon2
- ✅ Encrypt sensitive data (Plaid tokens)
- ✅ Use HTTPS in production
- ✅ Rate limit API endpoints
- ✅ Sanitize HTML output
- ✅ Check authentication on all protected routes

### DON'T
- ❌ Store passwords in plain text
- ❌ Commit secrets to git
- ❌ Use `eval()` or `exec()`
- ❌ Trust user input
- ❌ Disable CORS in production
- ❌ Log sensitive data
- ❌ Use outdated dependencies

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Instead, email security@nestegg.app with:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Performance Guidelines

### Backend
- Use async/await for I/O operations
- Add database indexes for frequent queries
- Implement pagination for large datasets
- Cache expensive calculations
- Use connection pooling

### Frontend
- Lazy load routes with React.lazy()
- Debounce search inputs
- Use React Query for caching
- Optimize images
- Minimize bundle size

## Documentation

### When to Document

**Always document:**
- New API endpoints
- Complex algorithms
- Configuration changes
- Database schema changes
- Security features

**Format:**
- Python: Docstrings (Google style)
- API: OpenAPI/Swagger (auto-generated)
- User-facing: Markdown files

### API Documentation

FastAPI auto-generates docs, but add descriptions:
```python
@router.post("/budgets", response_model=BudgetResponse)
async def create_budget(
    budget: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new budget.

    Args:
        budget: Budget creation payload
        current_user: Authenticated user
        db: Database session

    Returns:
        Created budget with ID

    Raises:
        HTTPException 400: Invalid budget data
        HTTPException 409: Budget already exists
    """
    # Implementation
```

## Getting Help

- **Documentation:** Read `backend/tests/README.md`
- **Ask Questions:** Open a GitHub Discussion
- **Report Bugs:** Open a GitHub Issue
- **Chat:** Join our Discord (link)

## Code Review Process

### For Reviewers

**Check:**
- [ ] Tests pass
- [ ] Code follows style guide
- [ ] No security vulnerabilities
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Database migrations are reversible

**Provide:**
- Constructive feedback
- Specific suggestions
- Praise for good work

### For Contributors

**Respond to:**
- All review comments
- CI failures
- Questions from reviewers

**Be:**
- Patient with feedback
- Open to suggestions
- Willing to iterate

## Release Process

1. Update version in `pyproject.toml` and `package.json`
2. Update CHANGELOG.md
3. Create release branch: `release/v1.2.3`
4. Run full test suite
5. Deploy to staging
6. QA testing
7. Merge to main
8. Create Git tag: `v1.2.3`
9. Deploy to production
10. Monitor for errors

## License

By contributing, you agree that your contributions will be licensed under the project's license (see LICENSE file).
