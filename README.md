# Nest Egg - Personal Finance Tracking Application

A comprehensive multi-tenant personal finance SaaS application for tracking transactions, investments, income vs expenses, with custom reporting and multi-user support.

## Features

- 📊 **Transaction Tracking**: Automatically sync transactions from banks via Plaid
- 🏷️ **Smart Labeling**: Custom labels with rule-based automation
- 💰 **Investment Tracking**: Asset allocation, performance analysis, and projections
- 📈 **Income vs Expenses**: Detailed analysis with customizable time periods
- 📅 **Custom Month Boundaries**: Define your own month-end dates
- 👥 **Multi-User Support**: Track finances individually or combined
- 📑 **Custom Reports**: Flexible aggregation logic for personalized insights
- 🔮 **Future Projections**: Calculate retirement and investment goals
- 🏠 **Manual Assets**: Track homes, treasuries, mortgages, and more

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

- [ ] Phase 1: Authentication and project foundation ✅
- [ ] Phase 2: Plaid integration and account management
- [ ] Phase 3: Transaction management and labeling
- [ ] Phase 4: Rule engine for automated categorization
- [ ] Phase 5: Investment tracking and asset allocation
- [ ] Phase 6: Dashboard and income vs expenses
- [ ] Phase 7: Prediction calculator
- [ ] Phase 8: Custom reporting engine
- [ ] Phase 9: Manual accounts and additional assets
- [ ] Phase 10: Webhooks and polish

---

Built with ❤️ using FastAPI, React, and modern web technologies.
