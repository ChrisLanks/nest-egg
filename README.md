# Nest Egg - Personal Finance Tracking Application

A comprehensive multi-tenant personal finance SaaS application for tracking transactions, investments, income vs expenses, with custom reporting and multi-user support.

## Features

- 📊 **Transaction Tracking**: Automatically sync transactions from banks via Plaid
- 🏷️ **Smart Labeling**: Custom labels with rule-based automation
- 💰 **Investment Analysis Dashboard**: Comprehensive 6-tab portfolio analysis
  - **Asset Allocation**: Interactive treemap visualization
  - **Sector Breakdown**: Holdings by financial sector (Tech, Healthcare, etc.)
  - **Future Growth**: Monte Carlo simulation with best/worst case scenarios
  - **Performance Trends**: Historical tracking with CAGR and YoY growth
  - **Risk Analysis**: Volatility, diversification scores, and concentration warnings
  - **Holdings Detail**: Sortable table with CSV export
- 📈 **Income vs Expenses**: Detailed analysis with customizable time periods
- 📅 **Custom Month Boundaries**: Define your own month-end dates
- 👥 **Multi-User Support**: Track finances individually or combined
- 📑 **Custom Reports**: Flexible aggregation logic for personalized insights
- 🔮 **Future Projections**: Calculate retirement and investment goals
- 🏠 **Manual Assets**: Track homes, treasuries, mortgages, and more
- 🤖 **Smart Snapshot Scheduler**: Automatic daily portfolio snapshots with load distribution

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database with JSONB support
- **Redis** - Caching and task queue
- **Celery** - Background task processing
- **SQLAlchemy 2.0** - Async ORM
- **Plaid** - Financial data aggregation

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Chakra UI** - Component library
- **React Query** - Server state management
- **Zustand** - Client state management
- **Recharts** - Data visualization

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (if running backend without Docker)
- Plaid API credentials (sign up at https://dashboard.plaid.com/signup)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nest-egg
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your Plaid API credentials
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

   This starts:
   - PostgreSQL (port 5432)
   - Redis (port 6379)
   - FastAPI API (port 8000)
   - Celery Worker (background tasks)
   - Celery Beat (task scheduler)
   - Flower (Celery monitoring at port 5555)

4. **Run database migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. **Set up frontend** (in a separate terminal)
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   npm run dev
   ```

   Frontend will be available at http://localhost:5173

### API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Celery Monitoring

View background task status at:
- Flower UI: http://localhost:5555

## Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload

# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Run tests
npm test

# Build for production
npm run build

# Preview production build
npm run preview
```

### Creating Database Migrations

```bash
cd backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Project Structure

```
nest-egg/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core utilities (auth, db, config)
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── crud/           # CRUD operations
│   │   ├── workers/        # Celery tasks
│   │   ├── middleware/     # Custom middleware
│   │   └── utils/          # Utility functions
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── features/      # Feature modules
│   │   ├── components/    # Shared components
│   │   ├── stores/        # Zustand stores
│   │   ├── services/      # API client
│   │   ├── hooks/         # Custom hooks
│   │   ├── utils/         # Utilities
│   │   └── types/         # TypeScript types
│   └── package.json       # npm dependencies
│
├── docker-compose.yml      # Docker services
└── README.md              # This file
```

## Key Concepts

### Multi-Tenancy

The application supports multiple organizations with complete data isolation:
- Each organization has multiple users
- All queries automatically filter by `organization_id`
- Row-level security ensures data isolation

### User Views

Users can view finances in three modes:
- **Person 1**: Individual view for first user
- **Person 2**: Individual view for second user
- **Combined**: Aggregated view of both users

All features respect the selected view mode.

### Transaction Deduplication

Transactions are deduplicated using a multi-layer approach:
1. Provider transaction ID (Plaid)
2. Content-based hashing (date + amount + merchant)
3. Database constraints prevent duplicates

### Background Sync

Celery tasks automatically sync data:
- **Daily**: Full sync of all accounts (2 AM)
- **Hourly**: Active accounts (accessed in last 7 days)
- **Webhook**: Real-time updates from Plaid
- **Manual**: On-demand sync button

### Multi-User Households

The application supports **multi-user households** where up to 5 people can share financial data while maintaining individual account ownership.

#### How It Works

1. **Individual Logins**: Each person has their own login credentials
2. **Household Invitation**: Primary user invites others via email
3. **Account Ownership**: Each user owns specific accounts
4. **View Modes**: Switch between individual and combined views
5. **Duplicate Detection**: Same bank account added by multiple users only counted once

#### Key Features

- **User View Selector**: Dropdown on all major pages (Dashboard, Investments, Cash Flow)
  - "Combined Household" - Shows all accounts (deduplicated)
  - Individual users - Shows only that user's accounts (owned + shared)
- **Household Limit**: Maximum 5 members per household
- **Account Sharing**: Users can share specific accounts with view/edit permissions
- **Deep Linking**: URL state persists user selection (`?user=<uuid>`)
- **RMD Calculations**: Age-specific Required Minimum Distribution per member
- **Deduplication**: SHA256 hash-based duplicate account detection

#### Setting Up a Household

**1. Send Invitation (Admin User)**
```bash
# Login as primary user
http://localhost:5173/login

# Navigate to Household Settings
Click avatar → "Household Settings"

# Send invitation
Click "Invite Member"
Enter: newmember@example.com
```

**2. Accept Invitation (New Member)**
```bash
# Register with invited email
http://localhost:5173/register
Email: newmember@example.com (must match invitation)
Password: [secure password]

# Accept invitation link
http://localhost:5173/accept-invite?code=<invitation-code>
Click "Accept Invitation"
```

**3. Use User View Selector**
```bash
# On any major page (Dashboard, Investments, Cash Flow)
- Select "Combined Household" to see all accounts
- Select individual user to see their accounts only
- URL updates with ?user=<uuid> for bookmarking
```

#### Database Schema

**New Tables:**
- `household_invitations` - Tracks invitation lifecycle
  - Status: pending, accepted, declined, expired
  - 7-day expiration by default
  - Unique invitation codes

- `account_shares` - Account sharing permissions
  - Share with specific users
  - View or edit permissions
  - Foreign keys with cascade delete

**New Columns:**
- `accounts.plaid_item_hash` - SHA256 hash for duplicate detection
- `users.is_primary_household_member` - Marks household owner

#### API Endpoints

**Household Management:**
```bash
POST   /api/v1/household/invite              # Send invitation (admin only)
GET    /api/v1/household/invitations         # List pending invitations
GET    /api/v1/household/invitation/{code}   # Get invitation details (public)
POST   /api/v1/household/accept/{code}       # Accept invitation (public)
DELETE /api/v1/household/invitations/{id}    # Cancel invitation (admin only)
GET    /api/v1/household/members             # List household members
DELETE /api/v1/household/members/{id}        # Remove member (admin only)
```

**User Filtering:**
All major endpoints accept optional `?user_id=<uuid>` parameter:
- `/api/v1/dashboard/summary?user_id=<uuid>`
- `/api/v1/holdings/portfolio?user_id=<uuid>`
- `/api/v1/holdings/rmd-summary?user_id=<uuid>`
- `/api/v1/income-expenses/summary?user_id=<uuid>`
- `/api/v1/accounts?user_id=<uuid>`

#### Testing Multi-User Features

**Scenario: Two users with shared account**

```bash
# 1. Create test accounts
User A: test@test.com (primary)
User B: test2@test.com

# 2. User A links Chase Checking
Login as test@test.com
Link Chase account via Plaid

# 3. User B links same Chase Checking
Login as test2@test.com
Link same Chase account (Plaid detects via plaid_item_hash)

# 4. Test view modes
- User A individual view: Shows Chase once
- User B individual view: Shows Chase once
- Combined view: Shows Chase once (deduplicated)
- Balance/transactions not double-counted
```

#### Backfill Script

For existing installations, populate hashes and primary members:

```bash
cd backend
./venv/bin/python app/scripts/backfill_account_hashes.py
```

This script:
- Calculates `plaid_item_hash` for existing accounts
- Sets `is_primary_household_member` for oldest user in each org
- Required after database migration

#### Security & Permissions

**Access Control:**
- Users can view **own accounts** + **explicitly shared accounts**
- Users **cannot** view other members' non-shared accounts
- Combined view shows all household accounts (respects organization_id)

**Admin Functions:**
Only `is_org_admin` users can:
- Send invitations
- Remove members (except self and primary member)
- Cancel pending invitations

**Row-Level Security:**
- All queries filter by `organization_id`
- Additional `account_ids` filter for user views
- Duplicate detection only within same household

### Investment Analysis

The application provides comprehensive portfolio analysis through six specialized tabs:

#### 1. Asset Allocation
- Interactive treemap visualization showing portfolio breakdown
- Drill-down capability to explore account and holding details
- Visual representation of asset distribution

#### 2. Sector Breakdown
- Horizontal bar chart showing holdings by financial sector
- Integrates with Alpha Vantage API for sector classification
- Displays Technology, Healthcare, Financials, Consumer sectors, etc.
- Shows holding count and percentage for each sector

#### 3. Future Growth Projections
- Monte Carlo simulation with 1000+ runs for realistic forecasting
- Adjustable parameters:
  - Annual Return (expected growth rate)
  - Volatility (risk/uncertainty)
  - Inflation Rate (purchasing power adjustment)
  - Time Horizon (1-30 years)
- Displays 6 projection lines:
  - Best Case (90th percentile)
  - Median (expected value)
  - Worst Case (10th percentile)
  - All available in both nominal and inflation-adjusted views

#### 4. Performance Trends
- Historical portfolio value tracking over time
- Time range selector: 1M, 3M, 6M, 1Y, ALL
- Performance metrics:
  - **Total Return**: Absolute and percentage gain/loss
  - **CAGR**: Compound Annual Growth Rate
  - **YoY Growth**: Year-over-year comparison
- Line chart with cost basis comparison
- Automatically uses mock data until real snapshots accumulate

#### 5. Risk Analysis
- **Overall Risk Score** (0-100): Composite metric with color-coded badge
  - Green (<40): Low Risk
  - Yellow (40-70): Moderate Risk
  - Red (>70): High Risk
- **Volatility**: Annualized standard deviation from 6-month data
- **Diversification Score**: Based on Herfindahl-Hirschman Index
- **Asset Class Allocation**: Bar chart of stocks, ETFs, bonds, cash, etc.
- **Top Concentrations**: Warnings for holdings >20% of portfolio

#### 6. Holdings Detail
- Sortable table with all holdings
- Columns: Ticker, Name, Shares, Price, Value, Cost Basis, Gain/Loss
- Filter by asset type
- Search by ticker or name
- CSV export functionality

### Portfolio Snapshot Scheduler

The application includes an intelligent background scheduler for daily portfolio snapshots:

#### How It Works
- **Offset-Based Distribution**: Each organization gets a unique time slot (0-24 hours)
  - Deterministic: Same org always runs at same time
  - Calculated from organization UUID hash
  - Spreads load evenly across 24 hours
- **Hourly Checks**: Scheduler wakes up every hour to check which orgs need snapshots
- **Smart Execution**: Only captures if:
  1. No snapshot exists for today
  2. Organization's scheduled time has passed
- **Startup Recovery**: On app restart, checks for missed snapshots and captures them
- **No Cron Required**: Runs as integrated FastAPI background task

#### Benefits
- Prevents all organizations from updating simultaneously
- Distributes database load across the day
- Resilient to server restarts
- Automatic with no external configuration
- Provides historical data for Performance Trends and Risk Analysis tabs

#### Example Timeline
```
Org A (UUID ending ...1234) → 3:45am UTC daily
Org B (UUID ending ...5678) → 3:12pm UTC daily
Org C (UUID ending ...9abc) → 9:30pm UTC daily
```

#### Manual Override
To manually trigger a snapshot (ignores schedule):
```bash
curl -X POST http://localhost:8000/api/v1/holdings/capture-snapshot \
  -H "Authorization: Bearer <your-token>"
```

## Plaid Integration Setup

1. Sign up for Plaid at https://dashboard.plaid.com/signup
2. Create a new application in the Plaid Dashboard
3. Get your `client_id` and `secret` (start with Sandbox)
4. Add credentials to `.env` file
5. For webhook testing in development, use ngrok:
   ```bash
   ngrok http 8000
   # Add the ngrok URL to Plaid webhook configuration
   ```

## Testing

### Backend Tests

```bash
cd backend
pytest                          # Run all tests
pytest tests/test_auth.py      # Run specific test file
pytest -v                       # Verbose output
pytest --cov=app               # With coverage
```

### Frontend Tests

```bash
cd frontend
npm test                        # Run all tests
npm test -- --coverage         # With coverage
npm run test:ui                # Interactive UI
```

## Deployment

### Production Checklist

- [ ] Generate secure `SECRET_KEY` and `MASTER_ENCRYPTION_KEY`
- [ ] Use managed PostgreSQL (AWS RDS, GCP Cloud SQL)
- [ ] Use managed Redis (ElastiCache, Cloud Memorystore)
- [ ] Configure production Plaid credentials
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS for production domains
- [ ] Set up Sentry for error tracking
- [ ] Configure backup strategy for database
- [ ] Set up monitoring and alerting
- [ ] Review security settings

## Common Tasks

### Add a New User to Existing Organization

```bash
# Via API (after login as org admin)
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass","first_name":"John","last_name":"Doe"}'
```

### Manually Trigger Plaid Sync

```bash
# Via Celery task
docker-compose exec celery_worker python -c "
from app.workers.tasks import sync_account_task
sync_account_task.delay('account-uuid-here')
"
```

### View Celery Tasks

Visit Flower UI: http://localhost:5555

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps db

# View logs
docker-compose logs db

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d
```

### Plaid Sandbox Test Credentials

For testing in Sandbox environment:
- **Username**: user_good
- **Password**: pass_good
- **PIN/MFA**: 1234 (if asked)

### Celery Tasks Not Running

```bash
# Check worker status
docker-compose logs celery_worker

# Restart worker
docker-compose restart celery_worker celery_beat
```

## Contributing

This is a personal project, but suggestions and bug reports are welcome!

1. Create an issue describing the bug or feature
2. Fork the repository
3. Create a feature branch
4. Make your changes with tests
5. Submit a pull request

## License

[Add your chosen license here]

## Support

For questions or issues:
- Check the [implementation plan](/.claude/plans/distributed-finding-lobster.md)
- Review API documentation at http://localhost:8000/docs
- Check Celery logs for background task issues

## Roadmap

- [x] Phase 1: Authentication and project foundation ✅
- [x] Phase 2: Plaid integration and account management ✅
- [x] Phase 3: Transaction management and labeling ✅
- [x] Phase 4: Rule engine for automated categorization ✅
- [x] Phase 5: Investment tracking and asset allocation ✅
  - [x] Asset Allocation treemap visualization
  - [x] Sector breakdown with Alpha Vantage integration
  - [x] Future growth Monte Carlo projections
  - [x] Performance trends with historical tracking
  - [x] Risk analysis (volatility & diversification)
  - [x] Holdings detail table with export
  - [x] Smart snapshot scheduler with offset distribution
- [x] Phase 6: Dashboard and income vs expenses ✅
- [ ] Phase 7: Prediction calculator
- [ ] Phase 8: Custom reporting engine
- [ ] Phase 9: Manual accounts and additional assets (partial)
- [ ] Phase 10: Webhooks and polish

---

Built with ❤️ using FastAPI, React, and modern web technologies.
