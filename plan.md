# Nest Egg - Personal Finance Tracking Application Implementation Plan

## Context

Building a comprehensive multi-tenant personal finance SaaS application from scratch. The application will track credit card transactions, investments, income vs expenses, and provide custom reporting with support for multiple users (person 1, person 2, and combined views).

**Why this change is needed:** Create a centralized platform to track all financial data beyond the 90-day limitation of services like Plaid, with advanced features like custom categorization rules, asset allocation tracking, future projections, and highly customizable reporting.

**Key Requirements:**
- Multi-user support with individual and combined financial views
- Long-term historical data retention (years of transactions, not just 90 days)
- Integration with Plaid for automated transaction/investment syncing
- Custom transaction labeling with rule engine for automation
- Investment tracking with asset allocation and performance analysis
- Custom month boundaries (e.g., month ending on 16th instead of 30th)
- Manual account entry support (homes, treasuries, mortgages)
- Custom reporting engine with flexible aggregation logic
- Future projection calculator

## Technology Stack

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 16 with JSONB support
- **ORM:** SQLAlchemy 2.0 with async support
- **Task Queue:** Celery with Redis broker
- **Cache:** Redis for caching and session management
- **Authentication:** JWT with Argon2 password hashing

### Frontend
- **Framework:** React 18 with TypeScript 5
- **Build Tool:** Vite
- **UI Library:** Chakra UI v2 (accessible, themeable)
- **State Management:** Zustand (UI state) + React Query (server state)
- **Charts:** Recharts (React-native charting)
- **Forms:** React Hook Form + Zod validation
- **Tables:** @tanstack/react-table
- **Routing:** React Router v6

### Infrastructure
- **Deployment:** Docker Compose (local development)
- **Database Migrations:** Alembic
- **API Integration:** Plaid Python SDK
- **Monitoring:** Structlog + Sentry (optional)

## Architecture Overview

### Multi-Tenant Design
- **Strategy:** Row-level isolation with `organization_id` on all tables
- **Middleware:** Automatic tenant filtering on all queries
- **Security:** PostgreSQL Row-Level Security (RLS) as additional layer

### Data Flow
```
User → React App → FastAPI API → PostgreSQL
                              ↓
                          Celery Worker → Plaid API
                              ↓
                          Redis (Queue/Cache)
```

### Key Architectural Patterns
1. **Feature-based organization** (frontend): Each feature (transactions, investments, etc.) is self-contained
2. **Service layer** (backend): Business logic separated from API routes
3. **CRUD pattern**: Generic CRUD operations with tenant filtering
4. **Adapter pattern**: Abstract financial provider interface (Plaid, future MX support)
5. **Background jobs**: Celery for scheduled syncs and rule processing

## Database Schema Highlights

### Core Tables

**organizations**
- `id`, `name`, `custom_month_end_day`, `timezone`, `created_at`

**users**
- `id`, `organization_id`, `email`, `password_hash`, `first_name`, `last_name`, `is_org_admin`
- Multi-user support: person1, person2, etc.

**accounts**
- `id`, `organization_id`, `user_id`, `name`, `account_type` (checking, credit_card, brokerage, retirement_401k, hsa, manual, etc.)
- `account_source` (plaid, mx, manual), `external_account_id`, `institution_name`, `current_balance`

**plaid_items** (credentials storage)
- `id`, `organization_id`, `user_id`, `item_id`, `access_token` (encrypted), `institution_name`, `cursor` (for incremental sync)

**transactions**
- `id`, `organization_id`, `account_id`, `external_transaction_id`, `date`, `amount`, `merchant_name`, `category_primary`, `is_pending`
- **UNIQUE constraint:** `(account_id, deduplication_hash)` to prevent duplicates

**transaction_hashes** (deduplication)
- Stores SHA256 hash of `date + amount + merchant + account_id` for duplicate detection

**labels** (user-defined categories)
- `id`, `organization_id`, `name`, `color`, `parent_label_id`, `is_income`, `is_system`

**transaction_labels** (many-to-many)
- Links transactions to labels, tracks which rule applied the label

**rules** (automation engine)
- `id`, `organization_id`, `name`, `priority`, `is_active`, `apply_to` (new_only, existing_only, both, single)
- `match_type` (all conditions must match vs any condition)

**rule_conditions**
- `field` (merchant_name, amount, category), `operator` (equals, contains, greater_than, regex), `value`

**rule_actions**
- `action_type` (add_label, remove_label, set_category, set_merchant), `action_value`

**investment_holdings**
- `id`, `account_id`, `ticker_symbol`, `security_name`, `quantity`, `current_price`, `current_value`, `asset_class` (domestic_equity, international_equity, bonds, cash), `as_of_date`

**investment_snapshots** (point-in-time for historical tracking)
- Daily snapshots of total value and asset allocation

**manual_assets**
- For homes, treasuries, mortgages, etc. with manual value updates

**custom_reports**
- `id`, `organization_id`, `name`, `report_config` (JSONB) storing aggregation logic

**background_jobs**
- Track sync jobs, rule applications, deduplication runs

### Indexes Strategy
- Composite indexes on `(organization_id, date)` for transactions
- GIN indexes on JSONB columns for flexible querying
- Unique indexes for deduplication

## Implementation Phases

### Phase 1: Project Foundation & Authentication (Week 1)

**Backend:**
- Set up FastAPI project structure (routes, models, schemas, services, crud, core)
- Configure PostgreSQL connection with SQLAlchemy async
- Implement Alembic migrations
- Create core models: Organization, User, RefreshToken
- JWT authentication system (access + refresh tokens)
- Password hashing with Argon2
- Registration and login endpoints
- Multi-tenant middleware for automatic `org_id` filtering

**Frontend:**
- Initialize Vite + React + TypeScript project
- Configure Chakra UI theme
- Set up React Router with protected routes
- Create authentication pages (Login, Register)
- Implement auth store (Zustand) for token management
- Configure Axios with JWT interceptors
- Create app layout (sidebar, header, page container)

**Docker:**
- `docker-compose.yml` with services: postgres, redis, api, celery_worker, celery_beat
- Dockerfile for FastAPI app
- Environment configuration (.env setup)

**Critical Files:**
- `app/main.py` - FastAPI app initialization
- `app/core/security.py` - JWT and password hashing
- `app/core/database.py` - Database session management
- `app/models/user.py` - User and Organization models
- `app/api/v1/auth.py` - Authentication endpoints
- `src/features/auth/` - Frontend auth components
- `src/stores/authStore.ts` - Auth state management
- `docker-compose.yml` - Container orchestration

### Phase 2: Account Management & Plaid Integration (Week 1-2)

**Plaid Setup:**
1. Sign up at https://dashboard.plaid.com/signup
2. Create application in Plaid Dashboard
3. Get `client_id` and `secret` (start with Sandbox environment)
4. Configure webhook URL (will need ngrok for local development)
5. Install Plaid Python SDK: `pip install plaid-python`

**Backend:**
- Account models (accounts, plaid_items)
- Credential encryption service (per-org encryption using derived keys)
- Plaid service layer:
  - `create_link_token()` - Initialize Plaid Link
  - `exchange_public_token()` - Exchange for access token
  - `sync_transactions()` - Fetch transactions with incremental sync
  - `sync_investments()` - Fetch holdings and balances
- Deduplication service (hash-based + provider ID)
- Account CRUD endpoints
- Plaid integration endpoints (`/integrations/plaid/*`)

**Frontend:**
- Settings page with Plaid Link integration
- react-plaid-link component for bank connection
- Account list and management UI
- Manual account creation form

**Celery Setup:**
- Configure Celery app with Redis broker
- Create sync tasks (initial and incremental)
- Schedule periodic syncs (daily, hourly for active accounts)

**Critical Files:**
- `app/models/account.py` - Account and PlaidItem models
- `app/services/plaid_service.py` - Plaid API wrapper
- `app/services/deduplication_service.py` - Duplicate prevention
- `app/utils/encryption.py` - Credential encryption
- `app/workers/celery_app.py` - Celery configuration
- `app/workers/tasks.py` - Background sync tasks
- `src/features/settings/components/PlaidConnection.tsx`

### Phase 3: Transaction Management & Labeling (Week 2-3)

**Backend:**
- Transaction models (transactions, transaction_hashes)
- Label models (labels, transaction_labels)
- Transaction CRUD with pagination and filtering
- Transaction service:
  - `get_transactions()` with filters (date range, account, labels, search)
  - `add_label()`, `remove_label()`, `bulk_label()`
  - `get_summary()` - Aggregated statistics
- Custom month boundary logic in date utilities
- Combined view support (aggregate multiple users)

**Frontend:**
- Transactions page with filterable table
- @tanstack/react-table for performant rendering
- Date range picker (preset periods + custom)
- User view toggle (Person 1, Person 2, Combined) in header
- Transaction labeling interface (inline editing)
- Label management (create, edit, delete labels)
- Search and advanced filters
- Transaction trends chart (spending over time)

**State Management:**
- Global filter store (date range, time period)
- User view store (current view selection)
- React Query for transaction data with caching

**Critical Files:**
- `app/models/transaction.py` - Transaction and Label models
- `app/services/transaction_service.py` - Transaction business logic
- `app/services/aggregation_service.py` - Combined view logic
- `app/utils/date_utils.py` - Custom month boundaries
- `src/features/transactions/pages/TransactionsPage.tsx`
- `src/features/transactions/components/TransactionTable.tsx`
- `src/components/common/UserViewToggle.tsx`
- `src/components/common/DateRangePicker.tsx`
- `src/stores/userViewStore.ts`
- `src/stores/filterStore.ts`

### Phase 4: Rule Engine (Week 3-4)

**Backend:**
- Rule models (rules, rule_conditions, rule_actions)
- Rule engine service:
  - `evaluate_condition()` - Check if transaction matches condition
  - `matches_rule()` - Evaluate all conditions (AND/OR logic)
  - `apply_action()` - Execute rule action (add label, set category)
  - `apply_rule()` - Apply rule to transactions (new/old/both)
  - `apply_all_rules()` - Run all active rules on new transaction
- Background task for rule application
- Rule CRUD endpoints with validation

**Frontend:**
- Rule builder interface (multi-step form)
- Condition builder (add multiple conditions with operators)
- Action selector (add labels, change categories)
- Application scope selector (new/old/both/single)
- Live preview of matching transactions
- Rule list with enable/disable toggle
- Create rule from transaction (pre-fill conditions)

**Critical Files:**
- `app/models/rule.py` - Rule, RuleCondition, RuleAction models
- `app/services/rule_engine.py` - Rule evaluation and execution
- `app/workers/rule_processor.py` - Background rule application
- `src/features/transactions/components/RuleBuilder.tsx`
- `src/features/transactions/components/RuleList.tsx`

### Phase 5: Investment Tracking (Week 4-5)

**Backend:**
- Investment models (investment_holdings, investment_snapshots, manual_assets)
- Investment service:
  - `sync_holdings()` - Fetch from Plaid investments API
  - `create_daily_snapshot()` - Store point-in-time data
  - `get_asset_allocation()` - Calculate allocation by class
  - `get_performance()` - Calculate gains/losses over time
  - `calculate_projections()` - Future value predictions
- Daily snapshot Celery task
- Investment endpoints (holdings, allocation, performance, projections)

**Frontend:**
- Investments page with multiple views
- Performance chart (line chart of portfolio value over time)
- Asset allocation pie chart with drill-down
- Account type breakdown (brokerage, HSA, Roth, etc.)
- Holdings table with current values and gains
- Interactive drill-down (click domestic → see holdings)
- Time period selector (consistent with transactions)

**Critical Files:**
- `app/models/investment.py` - Investment models
- `app/services/investment_service.py` - Investment calculations
- `app/workers/investment_sync.py` - Daily snapshot task
- `src/features/investments/pages/InvestmentsPage.tsx`
- `src/features/investments/components/AssetAllocationChart.tsx`
- `src/features/investments/components/PerformanceChart.tsx`

### Phase 6: Income vs Expenses & Dashboard (Week 5-6)

**Backend:**
- Income/expense analysis endpoints
- Dashboard summary service:
  - `get_net_worth()` - Total assets - debts
  - `get_debt_to_income()` - Calculate DTI ratio
  - `get_cash_flow()` - Income vs expenses over time
  - `get_income_sources()` - Breakdown by source
  - `get_expense_categories()` - Breakdown by category

**Frontend:**
- Dashboard page (default landing page)
- Net worth card with trend
- Debt to income ratio with rating
- Quick summary cards (total assets, debts, monthly spending)
- Recent transactions list
- Income vs expenses page
- Income sources breakdown chart
- Expense categories chart
- Cash flow trend over time

**Critical Files:**
- `app/services/dashboard_service.py` - Dashboard data aggregation
- `src/features/dashboard/pages/DashboardPage.tsx`
- `src/features/income-expenses/pages/IncomeExpensesPage.tsx`
- `src/features/income-expenses/components/IncomeVsExpensesChart.tsx`

### Phase 7: Prediction Calculator (Week 6)

**Backend:**
- Prediction service:
  - `calculate_future_value()` - Compound growth projection
  - `calculate_retirement_needs()` - Target calculation
  - `apply_tax_drag()` - After-tax calculations
- Prediction endpoints with configurable parameters

**Frontend:**
- Predictions page with interactive form
- Input fields: current value, market average, tax rate, years
- Real-time calculation as inputs change
- Projection chart showing growth curve
- Scenario comparison (optimistic, realistic, pessimistic)

**Critical Files:**
- `app/services/prediction_service.py` - Projection calculations
- `src/features/predictions/pages/PredictionsPage.tsx`
- `src/features/predictions/components/PredictionChart.tsx`

### Phase 8: Custom Reporting (Week 7)

**Backend:**
- Custom report models (custom_reports)
- Report execution engine:
  - Parse report configuration (JSONB)
  - Execute aggregation logic
  - Apply include/exclude rules
  - Calculate breakdowns
- Report CRUD endpoints
- Report execution endpoint with date range support

**Frontend:**
- Reports page with saved reports list
- Report builder interface:
  - Drag-and-drop source selection
  - Mathematical operators
  - Preview calculation results
  - Save report with name/description
- Report viewer with breakdown table
- Export to CSV functionality

**Critical Files:**
- `app/models/report.py` - CustomReport model
- `app/services/report_engine.py` - Report calculation
- `src/features/reports/pages/ReportsPage.tsx`
- `src/features/reports/components/ReportBuilder.tsx`

### Phase 9: Manual Accounts & Additional Assets (Week 7)

**Backend:**
- Manual asset models with value history
- Manual account CRUD endpoints
- Update reminders based on frequency
- Support for homes, mortgages, treasuries, etc.

**Frontend:**
- Manual account creation forms
- Asset type selector with custom types
- Value update interface
- Historical value chart
- Update reminders in UI

**Critical Files:**
- `app/models/manual_asset.py` - ManualAsset model
- `app/services/manual_account_service.py` - Manual account logic
- `src/features/settings/components/ManualAccountForm.tsx`

### Phase 10: Webhooks & Polish (Week 8)

**Backend:**
- Plaid webhook handlers:
  - Transaction updates
  - Holdings updates
  - Item errors (need reauth)
  - Pending expiration
- Webhook signature verification
- Webhook logging and monitoring

**Frontend:**
- Loading states and skeletons
- Error boundaries
- Empty states
- Responsive design refinement
- Mobile optimization
- Accessibility audit
- Performance optimization

**Testing:**
- Backend: pytest with async support, API endpoint tests
- Frontend: Vitest + React Testing Library
- E2E: Playwright for critical user flows
- Integration: MSW for API mocking

**Critical Files:**
- `app/api/webhooks.py` - Webhook endpoints
- `app/services/webhook_service.py` - Webhook processing
- `src/components/common/LoadingState.tsx`
- `src/components/common/ErrorBoundary.tsx`

## Critical Implementation Details

### Deduplication Strategy

**Multi-layer approach:**
1. **Provider ID** (primary): Use Plaid's `transaction_id` if available
2. **Content hash** (fallback): SHA256 of `date + amount + normalized_merchant + account_last_4`
3. **Database constraint**: UNIQUE on `(account_id, deduplication_hash)`

```python
def generate_deduplication_hash(transaction: dict) -> str:
    if transaction.get('provider_transaction_id'):
        return f"provider:{transaction['provider']}:{transaction['provider_transaction_id']}"

    # Normalize merchant name (lowercase, remove special chars, common suffixes)
    normalized_merchant = normalize_merchant_name(transaction['merchant_name'])

    components = [
        transaction['date'].isoformat(),
        f"{abs(transaction['amount']):.2f}",
        normalized_merchant,
        transaction.get('account_last_4', '')[:4]
    ]

    hash_input = '|'.join(components)
    return f"hash:{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"
```

### Solving the 90-Day Plaid Limitation

**Strategy:**
1. **Initial sync**: Fetch 90 days automatically when account connected
2. **CSV import**: Offer user option to upload historical transactions (parse common formats)
3. **Incremental sync**: Fetch last 7 days each sync to catch updates, but never delete old data
4. **Historical preservation**: Never delete transactions from database, even if Plaid doesn't return them

**Key principle:** Once a transaction is in the database, it stays forever unless explicitly deleted by user.

### Multi-User Combined Views

**Implementation:**
- Every API endpoint accepts `user_view` parameter (person_1, person_2, combined)
- Backend filters by `user_id` based on view:
  - person_1: `WHERE user_id = person1_id`
  - person_2: `WHERE user_id = person2_id`
  - combined: `WHERE user_id IN (person1_id, person2_id)`
- Frontend sends current view in request header (`X-User-View`)
- React Query cache keys include view, so data refetches on toggle

### Custom Month Boundaries

**Implementation:**
- Store `custom_month_end_day` in organizations table (e.g., 16)
- Date utility calculates custom month ranges:
  - If today is ≤ 16th: month is from (prev month 17th) to (this month 16th)
  - If today is > 16th: month is from (this month 17th) to (next month 16th)
- Apply to all date-based queries consistently

### Background Sync Strategy

**Celery Schedule:**
- **Daily at 2 AM**: Sync all active accounts
- **Hourly**: Sync accounts accessed in last 7 days
- **Webhook-triggered**: Real-time sync on Plaid notification
- **Manual**: On-demand button (rate-limited to 1/hour per account)

**Retry Logic:**
- Max 3 retries with exponential backoff
- Handle specific errors:
  - `ITEM_LOGIN_REQUIRED`: Mark account needs reauth, notify user
  - `RATE_LIMIT_EXCEEDED`: Wait and retry
  - `INSTITUTION_DOWN`: Retry up to 24 hours before alerting

## Project Structure

```
nest-egg/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                          # FastAPI app
│   │   ├── config.py                        # Settings
│   │   ├── dependencies.py                  # DI
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py                  # Auth endpoints
│   │   │       ├── accounts.py              # Account management
│   │   │       ├── transactions.py          # Transaction endpoints
│   │   │       ├── labels.py                # Label management
│   │   │       ├── rules.py                 # Rule CRUD
│   │   │       ├── investments.py           # Investment data
│   │   │       ├── reports.py               # Custom reports
│   │   │       ├── integrations.py          # Plaid/MX
│   │   │       └── webhooks.py              # Webhook handlers
│   │   ├── models/                          # SQLAlchemy models
│   │   ├── schemas/                         # Pydantic schemas
│   │   ├── services/                        # Business logic
│   │   ├── crud/                            # CRUD operations
│   │   ├── core/                            # Core utilities
│   │   ├── workers/                         # Celery tasks
│   │   ├── middleware/                      # Tenant isolation
│   │   └── utils/                           # Utilities
│   ├── alembic/                             # DB migrations
│   ├── tests/
│   ├── docker/
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── features/                        # Feature modules
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── transactions/
│   │   │   ├── investments/
│   │   │   ├── income-expenses/
│   │   │   ├── predictions/
│   │   │   ├── reports/
│   │   │   └── settings/
│   │   ├── components/                      # Shared components
│   │   │   ├── ui/
│   │   │   ├── layout/
│   │   │   ├── common/
│   │   │   └── charts/
│   │   ├── hooks/                           # Custom hooks
│   │   ├── stores/                          # Zustand stores
│   │   ├── services/                        # API layer
│   │   ├── utils/                           # Utilities
│   │   ├── types/                           # TypeScript types
│   │   ├── styles/                          # Theme
│   │   └── routes/                          # Routing
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
└── README.md
```

## Environment Configuration

### Backend `.env`
```env
# Database
DATABASE_URL=postgresql://nestegg:password@localhost:5432/nestegg

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
MASTER_ENCRYPTION_KEY=your-encryption-key-here

# Plaid
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret_key
PLAID_ENV=sandbox
PLAID_WEBHOOK_SECRET=your_webhook_secret

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Frontend `.env`
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_PLAID_ENV=sandbox
```

## Testing Strategy

### Backend Tests
- **Unit tests**: Services, utilities, deduplication logic
- **Integration tests**: API endpoints with test database
- **Sync tests**: Mock Plaid responses, verify data flow
- **Rule engine tests**: Condition evaluation, action execution

### Frontend Tests
- **Component tests**: Forms, charts, tables
- **Hook tests**: Custom hooks with React Query
- **Integration tests**: User flows with MSW
- **E2E tests**: Critical paths (login, connect Plaid, create rule)

### Test Coverage Goals
- Backend: >80% coverage
- Frontend: >70% coverage (focus on critical paths)

## Deployment

### Local Development
```bash
# Backend
cd backend
docker-compose up -d  # Start postgres, redis
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head  # Run migrations
uvicorn app.main:app --reload

# In separate terminal: Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# In separate terminal: Celery beat (scheduler)
celery -A app.workers.celery_app beat --loglevel=info

# Frontend
cd frontend
npm install
npm run dev
```

### Docker Compose (Recommended)
```bash
docker-compose up
# All services start together: postgres, redis, api, celery_worker, celery_beat
# Frontend: npm run dev (separate terminal)
```

### Production Considerations (Future)
- Use managed PostgreSQL (AWS RDS, GCP Cloud SQL)
- Use managed Redis (ElastiCache, Cloud Memorystore)
- Deploy API with Kubernetes or ECS
- Deploy frontend to Vercel/Netlify
- Set up Sentry for error tracking
- Configure CI/CD pipeline

## Verification Steps

After implementation, verify:

### 1. Authentication
- [ ] User can register with email/password
- [ ] User can login and receive JWT tokens
- [ ] Token refresh works correctly
- [ ] Protected routes redirect to login
- [ ] Logout clears tokens

### 2. Plaid Integration
- [ ] User can open Plaid Link modal
- [ ] Plaid Link successfully connects to bank (Sandbox)
- [ ] Accounts appear in database after connection
- [ ] Initial 90-day transaction sync completes
- [ ] Transactions appear in transactions table
- [ ] Investment holdings sync for investment accounts

### 3. Transactions
- [ ] Transactions page displays all transactions
- [ ] Date range filter works (last 30 days, this month, custom)
- [ ] User view toggle switches between Person 1, Person 2, Combined
- [ ] Search filters by merchant name
- [ ] User can create and apply labels to transactions
- [ ] Trends chart shows spending over time

### 4. Rule Engine
- [ ] User can create rule with conditions and actions
- [ ] Rule preview shows matching transactions
- [ ] Rule application to past transactions works
- [ ] New transactions automatically match rules
- [ ] Multiple conditions with AND/OR logic work

### 5. Investments
- [ ] Investment holdings display correctly
- [ ] Asset allocation pie chart shows breakdown
- [ ] Drill-down into asset class shows holdings
- [ ] Performance chart shows portfolio growth
- [ ] Daily snapshot task creates records

### 6. Dashboard
- [ ] Net worth calculation is correct
- [ ] Debt to income ratio displays
- [ ] Summary cards show accurate totals
- [ ] Data updates when user view toggles

### 7. Custom Reports
- [ ] User can create custom report with aggregation logic
- [ ] Report calculation produces correct result
- [ ] Saved reports persist across sessions
- [ ] Report respects date range selection

### 8. Background Jobs
- [ ] Celery worker processes tasks
- [ ] Daily sync task runs at scheduled time
- [ ] Manual sync button triggers immediate sync
- [ ] Failed jobs retry with backoff
- [ ] Webhook events trigger syncs

### 9. Multi-User Features
- [ ] Combined view shows data for multiple users
- [ ] Individual views show only that user's data
- [ ] All features (transactions, investments, dashboard) respect view selection

### 10. Edge Cases
- [ ] Deduplication prevents duplicate transactions
- [ ] Pending transactions update to posted
- [ ] Merchant name changes update existing transaction
- [ ] Custom month boundary calculations are correct
- [ ] Historical transactions beyond 90 days persist

## Key Dependencies

### Backend (requirements.txt)
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[argon2]==1.7.4
celery==5.3.6
redis==5.0.1
plaid-python==17.0.0
cryptography==42.0.0
python-dateutil==2.8.2
structlog==24.1.0
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "@chakra-ui/react": "^2.8.2",
    "@emotion/react": "^11.11.3",
    "@emotion/styled": "^11.11.0",
    "framer-motion": "^11.0.5",
    "@tanstack/react-query": "^5.20.0",
    "@tanstack/react-table": "^8.12.0",
    "zustand": "^4.5.0",
    "react-hook-form": "^7.50.0",
    "@hookform/resolvers": "^3.3.4",
    "zod": "^3.22.4",
    "axios": "^1.6.7",
    "recharts": "^2.12.0",
    "date-fns": "^3.3.1",
    "react-icons": "^5.0.1",
    "react-plaid-link": "^3.5.1"
  }
}
```

## Security Considerations

1. **Credential Encryption**: All Plaid access tokens encrypted at rest using per-org derived keys
2. **JWT Security**: Short-lived access tokens (15 min), long-lived refresh tokens (30 days)
3. **Password Hashing**: Argon2id (more secure than bcrypt)
4. **SQL Injection**: SQLAlchemy ORM prevents injection attacks
5. **XSS Prevention**: React escapes by default, validate all inputs
6. **CSRF**: JWT in Authorization header (not cookies) prevents CSRF
7. **Rate Limiting**: Implement on sensitive endpoints (login, sync)
8. **Webhook Verification**: Verify Plaid webhook signatures
9. **Multi-Tenant Isolation**: Row-level filtering + PostgreSQL RLS
10. **Audit Logging**: Log all sensitive operations

## Common Pitfalls to Avoid

1. **Deleting historical transactions**: Never delete transactions beyond Plaid's 90-day window
2. **Ignoring deduplication**: Always check for duplicates before inserting
3. **Hard-coding user references**: Always use current view from store/header
4. **Forgetting org_id filtering**: Every query must filter by organization_id
5. **Storing tokens unencrypted**: Always encrypt Plaid access tokens
6. **Blocking API calls**: Use Celery for long-running Plaid syncs
7. **Ignoring webhook signatures**: Always verify Plaid webhook authenticity
8. **Poor error handling**: Distinguish between user errors and system errors
9. **Missing indexes**: Always index foreign keys and frequently queried columns
10. **Inconsistent date handling**: Use consistent timezone (UTC) across system

## Success Metrics

After full implementation, the system should support:

- **Multiple organizations** with complete data isolation
- **Multiple users per organization** with individual and combined views
- **Years of transaction history** beyond Plaid's 90-day limitation
- **Automated categorization** through custom rules
- **Investment tracking** with asset allocation analysis
- **Custom financial reporting** with flexible aggregation
- **Future projections** with configurable assumptions
- **Manual asset entry** for homes, bonds, mortgages
- **Real-time updates** via Plaid webhooks
- **Reliable syncing** with retry logic and monitoring

## Next Steps After Implementation

1. **Add MX support** using the adapter pattern
2. **Implement budget tracking** with spending goals
3. **Add bill payment reminders** with due date tracking
4. **Create mobile app** using React Native (reuse business logic)
5. **Add data export** (CSV, PDF reports)
6. **Implement recurring transaction detection**
7. **Add split transaction support**
8. **Create savings goals tracking**
9. **Add net worth projections** to retirement age
10. **Implement tax optimization suggestions**

---

## Critical Files to Create First

These files are the foundation and should be created first:

1. **docker-compose.yml** - Start all services with one command
2. **backend/app/config.py** - Central configuration
3. **backend/app/core/database.py** - Database connection
4. **backend/app/core/security.py** - Authentication utilities
5. **backend/app/models/user.py** - User and Organization models
6. **backend/alembic/versions/001_initial.py** - Initial migration
7. **frontend/src/services/api.ts** - Axios configuration
8. **frontend/src/stores/authStore.ts** - Auth state
9. **frontend/src/stores/userViewStore.ts** - User view toggle
10. **frontend/src/stores/filterStore.ts** - Global filters

With your experience in the stack, implementation should take approximately 6-8 weeks working full-time, or 12-16 weeks part-time. The phased approach allows you to have a working MVP after 2-3 weeks (auth + Plaid + basic transactions), with features added incrementally.
