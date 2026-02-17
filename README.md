# Nest Egg - Personal Finance Tracking Application

A comprehensive multi-user personal finance application for tracking transactions, investments, budgets, and cash flow analysis with smart automation and proactive notifications.


<img width="1511" height="789" alt="image" src="https://github.com/user-attachments/assets/22a77cad-e244-4ad4-a775-b512f7ae5579" />

<img width="1512" height="982" alt="image" src="https://github.com/user-attachments/assets/09e0cf48-5d5e-47c3-a125-b54989f4c19a" />

<img width="1512" height="982" alt="image" src="https://github.com/user-attachments/assets/97dae7d3-f55f-4d1b-98a2-efe192f189a1" />

<img width="1512" height="797" alt="image" src="https://github.com/user-attachments/assets/3a2c1553-ce1e-4169-8933-8e3620357d47" />

<img width="1511" height="790" alt="image" src="https://github.com/user-attachments/assets/3a6e813e-5bf2-4dd8-ad36-39cae2156b66" />

<img width="1512" height="788" alt="image" src="https://github.com/user-attachments/assets/3f410abd-1fff-46a2-bb74-fb191cdc706e" />

<img width="1512" height="789" alt="image" src="https://github.com/user-attachments/assets/90bf447e-65f6-4160-b353-d88e132dc855" />


## ✨ Features

### 📊 **Transaction & Account Management**
- **Multi-Source Data Import**:
  - 🏦 **Plaid Integration**: Automatic bank sync with 11,000+ institutions
  - 🔗 **MX Integration**: Alternative banking aggregation
  - 📄 **CSV Import**: Manual upload for unsupported banks or historical data
- **Smart Deduplication**: Multi-layer duplicate detection ensures no double-counting
  - Provider transaction IDs (Plaid/MX)
  - Content-based hashing (date + amount + merchant + account)
  - Database unique constraints
  - **Guaranteed**: Same transaction from multiple sources only counted once
- **Column Visibility**: Customize transaction table columns (Date, Merchant, Account, Category, Labels, Amount, Status)
- **Bulk Operations**: Edit multiple transactions at once (category, labels, mark as reviewed)
- **Advanced Filtering**: Search by merchant, category, account, labels, amount range
- **Shift-Click Selection**: Select multiple transactions in a range

### 🏷️ **Smart Categorization & Labels**
- **Custom Categories**: Create your own category hierarchy with custom colors
- **Plaid Category Mapping**: Automatic mapping from Plaid's 350+ categories to your custom categories
- **Labels System**: Tag transactions with custom labels for flexible organization
- **Rule Engine**: Automated categorization based on:
  - Merchant name (exact, contains, starts with, ends with)
  - Amount (exact, greater than, less than, between)
  - Category matching
  - Multi-condition logic (AND/OR)
- **Smart Autocomplete**: Merchant and category selectors with search
- **Tax-Deductible Tracking**:
  - Pre-configured IRS categories (Medical & Dental, Charitable Donations, Business Expenses, Education, Home Office)
  - Export to CSV for tax software
  - Year-end reporting with date range selection

### 💰 **Investment Analysis Dashboard**
Comprehensive 6-tab portfolio analysis:
- **Asset Allocation**: Interactive treemap visualization with drill-down
- **Sector Breakdown**: Holdings by financial sector (Tech, Healthcare, Financials, etc.)
- **Future Growth**: Monte Carlo simulation with best/worst/median projections
  - Adjustable return rate, volatility, inflation, and time horizon
  - Inflation-adjusted and nominal value views
- **Performance Trends**: Historical tracking with CAGR and YoY growth
  - Time range selector (1M, 3M, 6M, 1Y, ALL)
  - Cost basis comparison
  - Mock data generator for testing (uses 7% annualized growth with volatility)
- **Risk Analysis**: Volatility, diversification scores, and concentration warnings
  - Overall risk score (0-100) with color-coded badges
  - Asset class allocation breakdown
- **Holdings Detail**: Sortable table with CSV export

### 📈 **Cash Flow Analytics (Income vs Expenses)**
- **Advanced Drill-Down**: Click any stat or chart element to filter
- **Time Period Selection**: Month, Quarter, Year, YTD, Custom range
- **Group By Options**: Category, Label, or Month
- **Interactive Visualizations**:
  - Summary statistics (Total Income, Total Expenses, Net Savings, Savings Rate)
  - Category breakdown pie chart with clickable legends
  - Trend line chart showing income vs expenses over time
  - Detailed transaction drilldowns
- **Label-Based Analysis**: Filter by custom labels for specialized tracking

### 💸 **Budget Management**
- **Flexible Periods**: Monthly, Quarterly, or Yearly budgets
- **Category-Based**: Set limits by spending category
- **Alert Thresholds**: Customizable warning levels (e.g., 80% of budget)
- **Proactive Notifications**:
  - Automatic daily checks for budget violations
  - High-priority alerts when over budget
  - Medium-priority warnings when approaching limit
- **Budget Tracking**: Real-time spending vs budget with progress bars
- **User-Specific**: Create budgets for household members or combined

### 🔔 **Smart Notification System**
- **Real-Time Alerts**: Auto-refresh every 30 seconds
- **Notification Types**:
  - 💰 Budget alerts (exceeding thresholds)
  - 💸 Large transaction warnings
  - 🔄 Account sync status
  - ⚠️ Low balance warnings
  - 📊 Cash flow forecast alerts (projected negative balances)
- **Notification Bell**: Unread count badge in top navigation
- **Mark as Read**: Individual or bulk "mark all read" functionality
- **Action Links**: Click notification to jump to relevant page
- **Test Endpoint**: `/api/v1/notifications/test` for testing (requires authentication)

### 📅 **Background Automation (Celery)**
Scheduled tasks for hands-free operation:
- **Daily Budget Alerts** (Midnight): Check all budgets and create notifications
- **Weekly Recurring Detection** (Monday 2am): Auto-detect recurring transactions/subscriptions
- **Daily Cash Flow Forecast** (6:30am): Check for projected negative balances
- **Daily Portfolio Snapshots** (11:59pm): Capture end-of-day holdings values
  - Smart offset-based scheduling distributes load across 24 hours
  - Each organization runs at a consistent time based on UUID hash

### 👥 **Multi-User Household Support**
- **Up to 5 Members**: Each with individual login credentials
- **View Modes**:
  - Combined Household: All accounts deduplicated
  - Individual: User's own accounts only
  - Other Members: View household members (read-only or edit permissions)
- **Account Sharing**: Grant view/edit permissions to specific users
- **Account Ownership**: Each user owns their connected accounts
- **Duplicate Detection**: Same bank account added by multiple users only counted once
  - Uses SHA256 hash of `institution_id + account_id`
  - Automatic on Plaid/MX sync
- **Deep Linking**: URL state preservation (`?user=<uuid>`)
- **RMD Calculations**: Age-specific Required Minimum Distribution per member

### 🏠 **Manual Assets & Accounts**
- **Manual Account Types**: Savings, Checking, Investment, Retirement, Loan, Mortgage, Credit Card, Other
- **Property Tracking**: Track real estate, vehicles, and other assets
- **Manual Balance Updates**: Update account balances directly
- **Investment Holdings**: Manually add stocks, ETFs, bonds, etc.

### 🔮 **Predictive Features**
- **Cash Flow Forecasting**: 30/60/90-day projections using recurring transaction patterns
- **Monte Carlo Simulations**: Investment growth modeling with uncertainty
- **Retirement Planning**: RMD calculations based on IRS tables
- **Negative Balance Alerts**: Proactive warnings when forecast shows insufficient funds

## 🛡️ Data Integrity & Deduplication

### **Guaranteed No Duplicates**

The application uses a **multi-layer deduplication strategy** to ensure transactions are never double-counted:

#### Layer 1: Provider Transaction IDs
- Plaid: Uses `transaction_id` from Plaid API
- MX: Uses `guid` from MX API
- Database unique constraint on `(account_id, plaid_transaction_id)`

#### Layer 2: Content-Based Hashing
- SHA256 hash of: `date + amount + merchant_name + account_id`
- Stored in `transaction_hash` column
- Database unique constraint prevents exact duplicates
- Works for CSV imports and manual entries

#### Layer 3: Household Account Deduplication
- SHA256 hash of: `institution_id + plaid_account_id`
- Stored in `plaid_item_hash` column
- When multiple users link the same bank account:
  - First user becomes the "owner"
  - Subsequent users' accounts are marked as duplicates
  - Only one copy appears in "Combined" view
  - Transactions not double-counted

#### Layer 4: Database Constraints
```sql
-- Unique constraints ensure database-level protection
UNIQUE (account_id, plaid_transaction_id)
UNIQUE (transaction_hash) WHERE transaction_hash IS NOT NULL
UNIQUE (plaid_item_hash) WHERE plaid_item_hash IS NOT NULL
```

### **Import Methods**

#### Plaid Sync
```bash
# Automatic daily sync
# Celery task: sync_account_task (scheduled)

# Manual sync via UI
Dashboard → Sync button on account card

# API endpoint
POST /api/v1/plaid/sync-account/{account_id}
```

#### MX Integration
```bash
# Similar to Plaid but uses MX API
# Configure MX credentials in .env:
MX_CLIENT_ID=your_mx_client_id
MX_API_KEY=your_mx_api_key
```

#### CSV Import
```bash
# Upload via UI
Transactions → Import CSV

# Format:
Date, Merchant, Amount, Category, Description
2024-01-15, Starbucks, -5.50, Dining, Coffee

# Deduplication: Automatic via transaction_hash
# Existing transactions skipped, new ones added
```

## 🚀 Technology Stack

### Backend
- **FastAPI** - Modern Python async web framework
- **PostgreSQL** - Primary database with JSONB support
- **Redis** - Caching and Celery task queue
- **Celery** - Background task processing with Beat scheduler
- **SQLAlchemy 2.0** - Async ORM with relationship loading
- **Alembic** - Database migrations
- **Plaid SDK** - Financial institution integration
- **MX Platform SDK** - Alternative banking aggregation
- **Pydantic v2** - Request/response validation
- **Passlib** - Password hashing with bcrypt
- **python-jose** - JWT token management

### Frontend
- **React 18** - UI library with hooks
- **TypeScript** - Type safety and IDE support
- **Vite** - Lightning-fast build tool
- **Chakra UI** - Accessible component library
- **React Query (TanStack)** - Server state management with caching
- **Zustand** - Client state management
- **Recharts** - Data visualization and charts
- **React Router v6** - Client-side routing
- **Axios** - HTTP client with interceptors
- **date-fns** - Date manipulation

## 📦 Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development without Docker)
- Plaid API credentials ([sign up](https://dashboard.plaid.com/signup))
- Optional: MX API credentials

### Setup with Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/nest-egg.git
   cd nest-egg
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API credentials
   ```

   Required variables:
   ```env
   # Database
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/nestegg

   # Auth
   SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
   MASTER_ENCRYPTION_KEY=your-encryption-key  # Generate with: openssl rand -hex 32

   # Plaid
   PLAID_CLIENT_ID=your_plaid_client_id
   PLAID_SECRET=your_plaid_secret
   PLAID_ENV=sandbox  # or development, production

   # Celery
   CELERY_BROKER_URL=redis://redis:6379/0
   CELERY_RESULT_BACKEND=redis://redis:6379/0
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

   This starts:
   - **PostgreSQL** (port 5432)
   - **Redis** (port 6379)
   - **FastAPI API** (port 8000)
   - **Celery Worker** (background tasks)
   - **Celery Beat** (task scheduler)
   - **Flower** (Celery monitoring at port 5555)

4. **Run database migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. **Set up frontend**
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   # Edit frontend/.env if needed (usually defaults are fine)
   npm run dev
   ```

   Frontend available at: http://localhost:5173

### Development Setup (Without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL and Redis locally
# Create database: createdb nestegg

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# In separate terminals, start Celery
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Accessing the Application

- **Frontend**: http://localhost:5173
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Celery Flower**: http://localhost:5555

### First Time Setup

1. **Register an account**: http://localhost:5173/register
2. **Verify email** (if email configured, otherwise auto-verified in dev)
3. **Link bank account**: Dashboard → Connect Account → Plaid Link
4. **Wait for sync**: Transactions should appear within 1-2 minutes
5. **Set up categories**: Categories page → Create custom categories
6. **Create budgets**: Budgets page → New Budget
7. **Test notifications**:
   ```bash
   # From browser console while logged in:
   fetch('/api/v1/notifications/test', {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${localStorage.getItem('token')}`,
       'Content-Type': 'application/json'
     }
   }).then(r => r.json()).then(console.log)
   ```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)

```env
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=<generate-with-openssl-rand-hex-32>
MASTER_ENCRYPTION_KEY=<generate-with-openssl-rand-hex-32>
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nestegg

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Plaid
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox  # sandbox, development, or production
PLAID_WEBHOOK_URL=https://your-domain.com/api/v1/plaid/webhook

# MX (Optional)
MX_CLIENT_ID=your_mx_client_id
MX_API_KEY=your_mx_api_key

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@nestegg.app

# Alpha Vantage (for sector data)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
```

#### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Nest Egg
```

## 📚 Key Concepts

### Multi-Tenancy & Organizations

- **Organization Isolation**: All data scoped by `organization_id`
- **Row-Level Security**: Every query automatically filters by organization
- **No Cross-Org Access**: Users can only see their organization's data
- **Household Model**: One organization = one household

### User View Modes

Users can view finances in three modes:

1. **Combined Household** - All accounts (deduplicated)
   - Shows total across all family members
   - Duplicate accounts counted once
   - Default view on login

2. **Individual (Person 1, Person 2, etc.)** - User-specific view
   - Only shows that user's owned accounts
   - Plus any accounts explicitly shared with them
   - URL parameter: `?user=<user_uuid>`

3. **Other Member (Read-Only/Edit)** - View another household member
   - Requires account sharing permissions
   - Can be view-only or edit access

All pages respect the selected view mode:
- Dashboard
- Transactions
- Income vs Expenses (Cash Flow)
- Investments
- Budgets

### Budget Alert System

**How It Works:**

1. **Budget Creation**: User creates budget (e.g., "Groceries $500/month, alert at 80%")
2. **Daily Check**: Celery task `check_budget_alerts` runs at midnight
3. **Threshold Calculation**: Compares actual spending to budget limit
4. **Notification Creation**: If over threshold, creates notification with priority:
   - **HIGH**: Spending ≥ 100% of budget (over limit)
   - **MEDIUM**: Spending ≥ alert threshold (e.g., ≥ 80%)
5. **User Notification**: Bell icon shows unread count, user clicks to view details

**Testing Budget Alerts:**

```bash
# Manually trigger the check
cd backend
celery -A app.workers.celery_app call check_budget_alerts

# Check logs
docker-compose logs celery_worker | grep -i budget
```

### Transaction Deduplication Flow

```
CSV Import / Plaid Sync / Manual Entry
    ↓
Check provider transaction ID (Plaid/MX)
    ↓ (if exists, skip)
Calculate content hash (date+amount+merchant+account)
    ↓ (if exists, skip)
Insert into database
    ↓ (DB constraint prevents duplicates)
Success - New transaction added
```

**Example:**

```python
# User imports CSV with transaction
Date: 2024-01-15, Merchant: Starbucks, Amount: -5.50

# Hash calculated:
hash = SHA256("2024-01-15|-5.50|Starbucks|account-uuid")
# = "a3f5b2c8..."

# Later, Plaid syncs same transaction
# Same hash calculated → Duplicate detected → Skip
```

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_deduplication.py

# Run with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test
npm test TransactionTable

# Interactive mode
npm run test:ui
```

### Manual Testing Scenarios

#### Test Multi-User Deduplication

1. User A logs in, links Chase Checking via Plaid
2. User B logs in (same household), links same Chase Checking
3. Switch to "Combined" view
4. ✅ Verify: Account appears only once
5. ✅ Verify: Balance not doubled
6. ✅ Verify: Transactions not duplicated

#### Test CSV Import Deduplication

1. Download transactions as CSV from Transactions page
2. Re-import the same CSV file
3. ✅ Verify: No duplicate transactions created
4. Check transaction count before and after import

#### Test Budget Alerts

1. Create budget: "Dining $100/month, alert at 80%"
2. Add transactions totaling $85 in Dining
3. Trigger alert check:
   ```bash
   celery -A app.workers.celery_app call check_budget_alerts
   ```
4. ✅ Verify: Notification appears in bell icon
5. ✅ Verify: Notification message shows "$85 of $100 (85%)"

## 🔍 Troubleshooting

### Common Issues

#### 1. **Notification Bell Not Updating**

**Symptoms**: No unread count, notifications not appearing

**Solutions**:
```bash
# Check backend logs
docker-compose logs api | grep notification

# Test notification endpoint
curl -X POST http://localhost:8000/api/v1/notifications/test \
  -H "Authorization: Bearer <your-token>"

# Check Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG
```

#### 2. **Celery Tasks Not Running**

**Symptoms**: Budget alerts not firing, snapshots not captured

**Solutions**:
```bash
# Check Celery worker status
docker-compose logs celery_worker

# Check Celery beat (scheduler)
docker-compose logs celery_beat

# View task queue in Flower
open http://localhost:5555

# Manually trigger task
celery -A app.workers.celery_app call check_budget_alerts
```

#### 3. **Duplicate Transactions After CSV Import**

**Symptoms**: Same transactions appear twice

**Diagnosis**:
```bash
# Check transaction hashes
SELECT id, merchant_name, amount, transaction_hash
FROM transactions
WHERE merchant_name = 'Starbucks'
ORDER BY date DESC
LIMIT 10;

# Check for NULL hashes (should not exist)
SELECT COUNT(*) FROM transactions WHERE transaction_hash IS NULL;
```

**Solution**:
```bash
# Backfill missing hashes (if needed)
cd backend
python app/scripts/backfill_transaction_hashes.py
```

#### 4. **Plaid Sync Failing**

**Symptoms**: "Sync failed" error, old transactions

**Solutions**:
```bash
# Check Plaid logs
docker-compose logs api | grep -i plaid

# Verify Plaid credentials
echo $PLAID_CLIENT_ID
echo $PLAID_SECRET

# Test Plaid connection
curl -X POST http://localhost:8000/api/v1/plaid/test-connection

# Re-link account
Dashboard → Account → "Re-link Account" button
```

#### 5. **Database Migration Issues**

**Symptoms**: "relation does not exist" errors

**Solutions**:
```bash
# Check current migration
cd backend
alembic current

# Check pending migrations
alembic history

# Run migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1

# Reset database (⚠️ destroys all data)
docker-compose down -v
docker-compose up -d
docker-compose exec api alembic upgrade head
```

#### 6. **Frontend Not Loading**

**Symptoms**: Blank page, API connection errors

**Solutions**:
```bash
# Check API is running
curl http://localhost:8000/health

# Check frontend environment
cd frontend
cat .env
# VITE_API_URL should be http://localhost:8000

# Clear browser cache
# Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

# Reinstall dependencies
rm -rf node_modules
npm install
npm run dev
```

### Debugging Tips

#### Enable Debug Logging

```python
# backend/app/config.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Check Celery Task Status

```bash
# List registered tasks
celery -A app.workers.celery_app inspect registered

# Check active tasks
celery -A app.workers.celery_app inspect active

# Check scheduled tasks (beat schedule)
celery -A app.workers.celery_app inspect scheduled
```

#### Database Query Debugging

```python
# Enable SQLAlchemy echo (shows all SQL queries)
# In backend/app/core/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True  # Add this line
)
```

## 🚀 Deployment

### Production Checklist

#### Security
- [ ] Generate secure `SECRET_KEY`: `openssl rand -hex 32`
- [ ] Generate secure `MASTER_ENCRYPTION_KEY`: `openssl rand -hex 32`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure HTTPS/SSL certificates
- [ ] Set restrictive CORS origins
- [ ] Enable rate limiting
- [ ] Set up Sentry error tracking

#### Database
- [ ] Use managed PostgreSQL (AWS RDS, GCP Cloud SQL, DigitalOcean)
- [ ] Configure automated backups (daily snapshots)
- [ ] Set up read replicas for scaling
- [ ] Configure connection pooling
- [ ] Set appropriate `max_connections` limit

#### Redis
- [ ] Use managed Redis (ElastiCache, Cloud Memorystore)
- [ ] Configure persistence (AOF or RDB)
- [ ] Set eviction policy
- [ ] Enable authentication

#### Celery
- [ ] Use separate worker and beat processes
- [ ] Configure autoscaling workers
- [ ] Set appropriate concurrency limits
- [ ] Monitor task queue depth
- [ ] Set up dead letter queue for failed tasks

#### External Services
- [ ] Configure production Plaid credentials
- [ ] Set up webhook URLs with HTTPS
- [ ] Configure email service (SendGrid, Mailgun, SES)
- [ ] Set up monitoring (Datadog, New Relic, CloudWatch)
- [ ] Configure logging aggregation (Loggly, Papertrail)

#### Performance
- [ ] Enable HTTP/2
- [ ] Configure CDN for static assets
- [ ] Set up database indexes
- [ ] Enable query caching
- [ ] Configure Redis caching

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Run migrations
docker-compose -f docker-compose.prod.yml run api alembic upgrade head

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Environment-Specific Settings

#### Production
```env
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS=https://app.nestegg.com
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/nestegg
REDIS_URL=redis://prod-redis:6379/0
PLAID_ENV=production
```

#### Staging
```env
ENVIRONMENT=staging
DEBUG=false
ALLOWED_ORIGINS=https://staging.nestegg.com
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/nestegg
REDIS_URL=redis://staging-redis:6379/0
PLAID_ENV=development
```

## 📝 Project Structure

```
nest-egg/
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── api/                  # API endpoints
│   │   │   └── v1/               # API version 1
│   │   │       ├── accounts.py           # Account management
│   │   │       ├── auth.py               # Authentication
│   │   │       ├── budgets.py            # Budget CRUD
│   │   │       ├── categories.py         # Category management
│   │   │       ├── dashboard.py          # Dashboard stats
│   │   │       ├── holdings.py           # Investment holdings
│   │   │       ├── household.py          # Multi-user management
│   │   │       ├── income_expenses.py    # Cash flow analytics
│   │   │       ├── labels.py             # Label management
│   │   │       ├── notifications.py      # Notification CRUD
│   │   │       ├── plaid.py              # Plaid integration
│   │   │       ├── rules.py              # Rule engine
│   │   │       └── transactions.py       # Transaction CRUD
│   │   ├── core/                 # Core utilities
│   │   │   ├── config.py                 # Settings management
│   │   │   ├── database.py               # DB connection pool
│   │   │   ├── security.py               # Auth utilities
│   │   │   └── encryption.py             # Field encryption
│   │   ├── models/               # SQLAlchemy models
│   │   │   ├── account.py                # Account model
│   │   │   ├── transaction.py            # Transaction model
│   │   │   ├── budget.py                 # Budget model
│   │   │   ├── category.py               # Category model
│   │   │   ├── label.py                  # Label model
│   │   │   ├── notification.py           # Notification model
│   │   │   ├── user.py                   # User model
│   │   │   └── ...                       # Other models
│   │   ├── schemas/              # Pydantic schemas
│   │   │   ├── account.py                # Account DTOs
│   │   │   ├── transaction.py            # Transaction DTOs
│   │   │   └── ...                       # Other schemas
│   │   ├── services/             # Business logic
│   │   │   ├── budget_service.py         # Budget calculations
│   │   │   ├── deduplication_service.py  # Duplicate detection
│   │   │   ├── notification_service.py   # Notification creation
│   │   │   ├── plaid_service.py          # Plaid sync logic
│   │   │   ├── rule_engine_service.py    # Rule evaluation
│   │   │   └── ...                       # Other services
│   │   ├── workers/              # Celery tasks
│   │   │   ├── celery_app.py             # Celery configuration
│   │   │   └── tasks/                    # Task modules
│   │   │       ├── budget_tasks.py       # Budget alert tasks
│   │   │       ├── holdings_tasks.py     # Snapshot tasks
│   │   │       ├── recurring_tasks.py    # Pattern detection
│   │   │       └── forecast_tasks.py     # Cash flow forecast
│   │   └── utils/                # Utility functions
│   ├── alembic/                  # Database migrations
│   │   └── versions/             # Migration files
│   ├── tests/                    # Backend tests
│   ├── requirements.txt          # Python dependencies
│   └── Dockerfile                # Backend container
│
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── features/             # Feature modules
│   │   │   ├── accounts/         # Account management
│   │   │   ├── auth/             # Authentication
│   │   │   ├── budgets/          # Budget UI
│   │   │   ├── categories/       # Category management
│   │   │   ├── dashboard/        # Dashboard widgets
│   │   │   ├── income-expenses/  # Cash flow analytics
│   │   │   ├── investments/      # Investment pages
│   │   │   ├── notifications/    # Notification UI
│   │   │   └── transactions/     # Transaction table
│   │   ├── components/           # Shared components
│   │   │   ├── Layout.tsx                # App layout with nav
│   │   │   ├── UserViewToggle.tsx        # View mode selector
│   │   │   ├── CategorySelect.tsx        # Category autocomplete
│   │   │   ├── MerchantSelect.tsx        # Merchant autocomplete
│   │   │   ├── RuleBuilderModal.tsx      # Rule creation UI
│   │   │   └── ...                       # Other components
│   │   ├── contexts/             # React contexts
│   │   │   └── UserViewContext.tsx       # User view state
│   │   ├── services/             # API client
│   │   │   └── api.ts                    # Axios instance
│   │   ├── hooks/                # Custom hooks
│   │   ├── utils/                # Utilities
│   │   ├── types/                # TypeScript types
│   │   └── App.tsx               # Root component
│   ├── package.json              # npm dependencies
│   ├── vite.config.ts            # Vite configuration
│   └── Dockerfile                # Frontend container
│
├── docker-compose.yml            # Development services
├── docker-compose.prod.yml       # Production services
├── .env.example                  # Environment template
└── README.md                     # This file
```

## 🛠️ Common Tasks

### Add New User to Household

```bash
# Option 1: Via household invitation (recommended)
# 1. Login as admin user
# 2. Navigate to Household Settings
# 3. Click "Invite Member"
# 4. Enter email address
# 5. New user registers with invited email
# 6. Accept invitation via link

# Option 2: Via API (direct creation)
curl -X POST http://localhost:8000/api/v1/household/invite \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com"}'
```

### Manually Sync Plaid Account

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/plaid/sync-account/<account-id> \
  -H "Authorization: Bearer <token>"

# Via Celery task
docker-compose exec celery_worker python -c "
from app.workers.tasks.plaid_tasks import sync_account_task
sync_account_task.delay('<account-uuid>')
"
```

### Export Transactions to CSV

```bash
# Via UI
Transactions → Export CSV button

# Via API
curl -X GET "http://localhost:8000/api/v1/transactions/export?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <token>" \
  -o transactions.csv
```

### Backfill Account Hashes (One-Time Migration)

```bash
cd backend
python app/scripts/backfill_account_hashes.py

# This script:
# - Calculates plaid_item_hash for existing accounts
# - Sets is_primary_household_member for oldest user
# - Required after database migration
```

### Create Database Backup

```bash
# PostgreSQL dump
docker-compose exec db pg_dump -U postgres nestegg > backup_$(date +%Y%m%d).sql

# Restore from backup
docker-compose exec -T db psql -U postgres nestegg < backup_20240115.sql
```

### View Celery Task Monitoring

```bash
# Flower UI
open http://localhost:5555

# CLI monitoring
celery -A app.workers.celery_app inspect active
celery -A app.workers.celery_app inspect registered
celery -A app.workers.celery_app inspect stats
```

## ⚠️ Known Issues & Important Notes

### 1. **Celery Worker Must Be Running**

Budget alerts, recurring detection, and portfolio snapshots **require Celery** to be running:

```bash
# Check if running
docker-compose ps celery_worker celery_beat

# Start if not running
docker-compose up -d celery_worker celery_beat
```

Without Celery:
- ❌ Budget alerts won't fire
- ❌ Recurring transactions won't be detected
- ❌ Portfolio snapshots won't be captured
- ❌ Cash flow forecasts won't generate alerts

### 2. **First Portfolio Snapshot Takes 24 Hours**

The smart snapshot scheduler distributes organizations across 24 hours. Your first snapshot may not appear immediately:

- Each org assigned a time slot based on UUID hash
- Check your org's scheduled time: `SELECT organization_id, calculated_offset FROM organizations`
- Manual override: `POST /api/v1/holdings/capture-snapshot`

### 3. **Plaid Sandbox Limitations**

When using Plaid Sandbox environment:

- ⚠️ Test institutions only (Chase, BoA, Wells Fargo, etc.)
- ⚠️ Fixed test credentials: `user_good` / `pass_good`
- ⚠️ Limited to 100 transactions per account
- ⚠️ No real-time updates (manual sync required)
- ✅ Switch to Development or Production for real banks

### 4. **Transaction Dedupe Only Within Organization**

Deduplication is **organization-scoped**:

- ✅ Same transaction imported twice → Deduped
- ✅ Same bank account added by household members → Deduped
- ❌ Same transaction across different organizations → Both kept (correct behavior)

### 5. **Category Mapping Persistence**

When you map a Plaid category to a custom category:

- Mapping stored in `category_mappings` table
- Applies to **all future transactions** from Plaid
- Existing transactions **not updated** (run manual recategorization if needed)

### 6. **Notification Bell Requires Login**

The test notification endpoint requires authentication:

```javascript
// From browser console while logged in:
fetch('/api/v1/notifications/test', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`,
    'Content-Type': 'application/json'
  }
})
```

### 7. **Multi-User View Permission Complexity**

User view permissions can be confusing:

- **Combined View**: Shows all household accounts (deduplicated)
- **Individual View**: Shows user's owned accounts + shared accounts
- **Edit Permissions**: Only owner can edit account details (name, balance)
- **Transaction Permissions**: All household members can edit transactions

### 8. **CSV Import Format Requirements**

CSV imports require these columns (order doesn't matter):

```csv
Date,Merchant,Amount,Category,Description
2024-01-15,Starbucks,-5.50,Dining,Morning coffee
```

- **Date**: YYYY-MM-DD format
- **Amount**: Negative for expenses, positive for income
- **Category**: Must match existing category name
- **Optional**: Description, Account

## 🗺️ Roadmap

### ✅ Completed Features

- [x] Authentication and user management
- [x] Plaid integration with automatic sync
- [x] Multi-user household support with deduplication
- [x] Transaction management with bulk operations
- [x] Rule engine for automated categorization
- [x] Custom categories with Plaid mapping
- [x] Label system for flexible tagging
- [x] Budget management with alerts
- [x] Notification system with real-time updates
- [x] Investment tracking with 6-tab analysis
- [x] Cash flow analytics with drill-down
- [x] Tax-deductible transaction tracking
- [x] CSV import with deduplication
- [x] Smart portfolio snapshot scheduler
- [x] Celery background tasks

### 🚧 In Progress

- [ ] MX integration (alternative to Plaid)
- [ ] Manual account improvements
- [ ] Debt payoff planner (Phase 3)
- [ ] Custom reports builder (Phase 3)

### 🔮 Future Features

- [ ] Multi-year trend analysis
- [ ] Subscription tracker
- [ ] Cash flow forecasting
- [ ] Mobile app (React Native)
- [ ] Receipt OCR and attachment storage
- [ ] Bill payment reminders
- [ ] Savings goals with progress tracking
- [ ] Net worth tracking over time
- [ ] Advanced investment analytics (Sharpe ratio, alpha, beta)
- [ ] Tax bracket optimization
- [ ] White-label SaaS offering

## 🐛 Recent Bug Fixes

### Navigation Dropdown Menu (Fixed)
- **Issue**: Dropdown menus stayed open after clicking items
- **Fix**: Implemented render prop pattern with explicit `onClose()` handlers
- **Commit**: `bdf96c5`

### Bulk Visibility Route Conflict (Fixed)
- **Issue**: `/accounts/bulk-visibility` endpoint returning 422 errors
- **Root Cause**: Route ordering - catch-all `/{account_id}` matched before specific route
- **Fix**: Moved `/bulk-visibility` route before `/{account_id}` route
- **Impact**: Hide All/Show All button now works correctly
- **Commit**: `bdf96c5`

### Transaction Duplicate Keys (Fixed)
- **Issue**: React warning about duplicate keys in transaction table
- **Fix**: Added unique prefixes (`desktop-${txn.id}`, `mobile-${txn.id}`)

### Tax Export 401 Error (Fixed)
- **Issue**: CSV export failing with authentication error
- **Fix**: Use axios with credentials instead of direct fetch

### Rule Builder Errors (Fixed)
- **Issue**: Category and merchant selectors causing crashes
- **Fix**: Added optional chaining and null checks

### Investment Charts 0/N/A (Fixed)
- **Issue**: Performance trends showing 0% and N/A
- **Fix**: Corrected mock data calculation to use proper growth formula

## 📄 License

[Add your chosen license here]

## 🤝 Contributing

This is a personal project, but suggestions and bug reports are welcome!

1. Create an issue describing the bug or feature
2. Fork the repository
3. Create a feature branch (`git checkout -b feature/amazing-feature`)
4. Make your changes with tests
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📞 Support

For questions or issues:

- **Documentation**: Review this README
- **Implementation Plan**: Check `/.claude/plans/distributed-finding-lobster.md`
- **API Docs**: http://localhost:8000/docs
- **Celery Monitoring**: http://localhost:5555
- **Database Logs**: `docker-compose logs db`
- **API Logs**: `docker-compose logs api`
- **Celery Logs**: `docker-compose logs celery_worker`

## 🙏 Acknowledgments

Built with:
- **FastAPI** - Modern Python web framework
- **React** - UI library
- **Chakra UI** - Component library
- **Plaid** - Financial data aggregation
- **Celery** - Task queue
- **PostgreSQL** - Database
- **Redis** - Caching
- **SQLAlchemy** - ORM
- **Recharts** - Data visualization

---

**Built with ❤️ for personal finance management**

_Last Updated: February 2024_
