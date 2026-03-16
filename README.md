# Nest Egg - Personal Finance Tracking Application

A comprehensive multi-user personal finance application for tracking transactions, investments, budgets, retirement planning, and cash flow analysis with smart automation and proactive notifications.

The real power in this tool, is the ability to invite others to your household (up to 5). Doing so will allow all cashflow trends, retirement data, debt planning, etc to be analyzed together allowing an accurate, single, holistic view. However, individual views are still accesable. You can change this in the top right corner of the page always. You can see the financial data of your personal account, and/or a significant other. The tool is also smart enough to de-duplicate the accounts. If you both have the mortgage or the same credit card, it will only show up once in the merged, combined household, view.
In addition, a household member can grant permissions to other household members to specific tools, ensuring a household user's settings cannot be changed without permission. (See more detail below).


## Screenshots
Note: there is dark mode and light mode

<img width="1512" height="860" alt="image" src="https://github.com/user-attachments/assets/bee8102d-25fd-4c2c-84a5-f8e738ea9318" />

<img width="1512" height="863" alt="image" src="https://github.com/user-attachments/assets/08741b93-3644-44d3-a1fe-5b5f808782f7" />

<img width="1512" height="864" alt="image" src="https://github.com/user-attachments/assets/8182c38e-d810-49db-9b58-a01d74b6061f" />

<img width="1510" height="861" alt="image" src="https://github.com/user-attachments/assets/e74ce71d-93cf-4706-80e3-304665a36c6b" />

<img width="1512" height="862" alt="image" src="https://github.com/user-attachments/assets/10066761-a116-4d4b-aa97-d33e9b2e954f" />

<img width="1512" height="861" alt="image" src="https://github.com/user-attachments/assets/5dc2eede-b4a8-41e7-a85f-06530cee72ee" />

<img width="1512" height="860" alt="image" src="https://github.com/user-attachments/assets/1bafa5e7-5146-4576-a363-99ee782033fa" />


<img width="1511" height="790" alt="image" src="https://github.com/user-attachments/assets/3a6e813e-5bf2-4dd8-ad36-39cae2156b66" />

<img width="1512" height="788" alt="image" src="https://github.com/user-attachments/assets/3f410abd-1fff-46a2-bb74-fb191cdc706e" />

<img width="1512" height="863" alt="image" src="https://github.com/user-attachments/assets/4f5b17c6-64ca-4053-ad4c-3076e4cbab1d" />


<img width="1512" height="789" alt="image" src="https://github.com/user-attachments/assets/90bf447e-65f6-4160-b353-d88e132dc855" />

<img width="1512" height="863" alt="image" src="https://github.com/user-attachments/assets/0b1aa5c8-874e-46c8-8c01-d4a065543c52" />

<img width="1511" height="860" alt="image" src="https://github.com/user-attachments/assets/e39f9043-138b-469f-9034-50565e8bfdf0" />

<img width="1508" height="862" alt="image" src="https://github.com/user-attachments/assets/a35632c7-59c4-43b9-accb-3184be3cc262" />

<img width="1512" height="860" alt="image" src="https://github.com/user-attachments/assets/b5958a54-728f-4351-9b51-0c778212bc57" />

<img width="1512" height="861" alt="image" src="https://github.com/user-attachments/assets/60531ae3-8c1a-4cb4-9b2a-3ade7502e460" />


## Views

<img width="1512" height="861" alt="image" src="https://github.com/user-attachments/assets/9e6765e0-a777-4515-8826-3093040ab9fe" />

<img width="1512" height="860" alt="image" src="https://github.com/user-attachments/assets/d56f9f6f-03cb-4794-8a53-0680db50194a" />

<img width="1512" height="859" alt="image" src="https://github.com/user-attachments/assets/26e7aec8-f0de-4041-8820-65343b397d73" />

## Permissions

<img width="1512" height="860" alt="image" src="https://github.com/user-attachments/assets/94fb5578-fb31-4aa9-8275-0d1fab99f75f" />

<img width="1512" height="861" alt="image" src="https://github.com/user-attachments/assets/dfc2cf4a-5095-40ff-97ae-02376c5f2442" />

<img width="454" height="590" alt="image" src="https://github.com/user-attachments/assets/f5396561-8d8e-4730-a1f5-48aa58437095" />


## Features

- **Transaction & Account Management** — multi-source import (Plaid, Teller, MX, CSV), smart deduplication, bulk operations, advanced filtering
- **Smart Categorization** — custom categories, automatic mapping, rule engine, tax-deductible tracking
- **Investment Dashboard** — 10-tab analysis: allocation, sectors, Monte Carlo growth, performance trends, risk analysis, Roth conversion, tax-loss harvesting, dividend income
- **Cash Flow Analytics** — income vs expenses with drill-down, time periods, category/label grouping
- **Budget Management** — flexible periods, category-based limits, proactive alerts, shared budgets
- **Retirement Planner** — Monte Carlo simulation, Social Security estimator, healthcare cost modeling, scenario comparison
- **Multi-User Households** — up to 5 members, combined/individual views, account deduplication
- **Guest Access** — invite external users (family, financial advisors) to view or edit household data without joining as members
- **RBAC Permissions** — fine-grained per-action grants, immutable audit log, per-page UI enforcement
- **Notifications** — real-time alerts for budgets, large transactions, low balances, forecasts; optional email delivery
- **Background Automation** — Celery tasks for budget checks, recurring detection, portfolio snapshots, data retention
- **Manual Assets** — property, vehicle, crypto tracking with auto-valuation (RentCast, MarketCheck)
- **Predictive Features** — cash flow forecasting, Monte Carlo simulations, negative balance alerts
- **Dark Mode** — light/dark/system toggle with semantic color tokens across all components
- **Identity Providers** — built-in JWT + pluggable Cognito, Keycloak, Okta, Google OIDC
- **Financial Health Score** — composite wellness score from savings rate, emergency fund, debt-to-income, retirement progress
- **Net Worth Milestones** — threshold alerts and all-time-high notifications
- **Transaction Notes & Flagged for Review** — free-text notes, household review workflow, flagged filter
- **Investment Fee Analyzer** — fee drag projections, fund overlap detection, low-cost alternatives
- **Year-in-Review** — annual financial summary with YoY comparison
- **Unified Financial Calendar** — bills + subscriptions + income with toggles and projected daily balance
- **Education Planning** — 529 contribution tracking and college cost projections
- **Rental Property P&L** — per-property profit & loss with Schedule E categories and cap rate
- **FIRE Planning** — financial independence calculator, savings rate tracking, coast FIRE projections
- **Debt Payoff** — snowball/avalanche strategies, payoff timeline, interest saved projections
- **Subscription Tracking** — recurring charge detection, annual cost summaries, cancellation reminders
- **Tax Lot Tracking** — cost basis methods (FIFO, LIFO, specific ID), realized/unrealized gains
- **Portfolio Rebalancing** — target allocation drift alerts, rebalance suggestions
- **Dividend & Investment Income** — track dividends, interest, capital gain distributions with DRIP support, yield-on-cost, and monthly trend charts
- **Tax Advisor** — age-aware tax insights: LTCG 0% bracket, Social Security taxation, IRMAA planning, NII surtax, RMD planning, Roth conversion windows
- **Enhanced Trends** — net worth history, investment performance (winners/losers), spending velocity, cash flow history, investment income trend
- **Centralized Financial Constants** — single-source tax rates, contribution limits, RMD tables, and thresholds (`backend/app/constants/financial.py`) for easy annual updates
- **Security** — rate limiting, CSRF, encryption at rest, MFA, GDPR compliance, webhook verification

> **Full details**: [docs/features.md](docs/features.md)

## Technology Stack

### Backend
- **FastAPI** + **SQLAlchemy 2.0** + **PostgreSQL** + **Redis** + **Celery**
- **Plaid**, **Teller**, **MX** bank integrations (all optional)
- **Yahoo Finance**, **Finnhub**, **Alpha Vantage** market data
- **Pydantic v2**, **Passlib** (bcrypt), **python-jose** (JWT), **Cryptography** (AES-256)
- **Prometheus** metrics, **Sentry** error tracking

### Frontend
- **React 18** + **TypeScript** + **Vite** + **Chakra UI**
- **TanStack Query**, **Zustand**, **Recharts**, **React Router v6**, **Axios**

## Quick Start

### Prerequisites

- **Docker** — for PostgreSQL and Redis (your user must be in the `docker` group)
- **Python 3.11+** — backend API
- **Node.js 18+** — frontend dev server
- **Git**
- Banking providers are **optional** — the app works without any of them (manual accounts + CSV import)

### Setup & Run

```bash
git clone https://github.com/yourusername/nest-egg.git
cd nest-egg

# One-command setup (env files, Docker services, Python venv, npm install, DB migrations)
./scripts/dev-setup.sh

# Start all services (backend, celery, frontend) — Ctrl+C to stop
./scripts/dev-run.sh
```

Run options:
```
--skip-docker      Don't start Docker services (already running)
--skip-celery      Don't start Celery worker/beat
--skip-frontend    Don't start frontend dev server
--skip-backend     Don't start backend API server
```

Setup options:
```
--skip-docker      Skip Docker Compose services
--skip-frontend    Skip frontend setup
--skip-backend     Skip backend setup
--seed-user        Create test@test.com with mock data (password: test1234)
--seed-user2       Create test2@test.com with mock data (password: test1234)
--yes              Answer yes to all prompts (non-interactive)
```

> **Seed test data** to get started quickly with pre-populated accounts, transactions, investments, and categories:
> ```bash
> ./scripts/dev-setup.sh --seed-user                    # single test user
> ./scripts/dev-setup.sh --seed-user --seed-user2       # both users (for household testing)
> ```

### Accessing the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs _(dev mode only)_ |
| Celery Flower | http://localhost:5555 |

If you ran setup with `--seed-user`, log in as `test@test.com` / `test1234`. Otherwise, register at http://localhost:5173/register.

### Production Deployment

```bash
./scripts/prod/setup.sh        # interactive env config wizard, generates secure keys
./scripts/prod/run.sh           # builds and starts the full Docker stack
./scripts/prod/run.sh status    # health check all services
```

> **Full guide**: [docs/deployment.md](docs/deployment.md)

### Makefile Shortcuts

A `Makefile` wraps common development commands:

```bash
make dev              # Start all services (same as ./scripts/dev-run.sh)
make test             # Run all tests (backend + frontend)
make test-backend     # Run backend tests only
make test-frontend    # Run frontend tests only
make test-coverage    # Tests with coverage reports
make lint             # Run all linters
make format           # Format all code
make db-migrate       # Run database migrations
make db-revision      # Create new Alembic migration
make db-shell         # Open PostgreSQL shell
make docker-up        # Start Docker services
make docker-down      # Stop Docker services
make health           # Check health of all services
make ci               # Run full CI checks locally (lint + test)
```

Run `make help` for the full list.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/features.md](docs/features.md) | Detailed feature descriptions, deduplication strategy, data integrity |
| [docs/configuration.md](docs/configuration.md) | Complete environment variable reference, banking provider comparison |
| [docs/deployment.md](docs/deployment.md) | Production deployment, Docker commands, scaling, backups, identity providers |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues, debugging tips, CLI recipes |
| [docs/MONITORING.md](docs/MONITORING.md) | Prometheus metrics, structured logging, Sentry, alerting |
| [docs/TELLER_API.md](docs/TELLER_API.md) | Teller API integration details and provider comparison |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | Banking provider setup (Plaid, Teller, MX), market data sources |
| [SECURITY.md](SECURITY.md) | Secrets management, rotation procedures, security checklist |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow, code standards, PR process |

## Project Structure

```
nest-egg/
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── api/v1/              # API endpoints (40+ modules)
│   │   ├── constants/            # Centralized financial rules (tax rates, limits, RMD tables)
│   │   ├── core/                # Config, database, security, encryption
│   │   ├── middleware/          # CSRF, rate limiting, security headers
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic, identity providers, market data
│   │   └── workers/             # Celery tasks
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Backend tests
│   └── Dockerfile
│
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── features/            # Feature modules (accounts, auth, budgets, etc.)
│   │   ├── components/          # Shared components
│   │   ├── contexts/            # React contexts
│   │   ├── services/            # API client
│   │   ├── stores/              # Zustand state stores
│   │   └── hooks/               # Custom hooks
│   └── Dockerfile
│
├── scripts/
│   ├── dev-setup.sh             # One-command dev setup
│   ├── dev-run.sh               # Start all dev services
│   └── prod/
│       ├── setup.sh             # Interactive production .env generator
│       └── run.sh               # Production Docker Compose orchestrator
│
├── docs/                        # Documentation
├── docker-compose.yml           # Production services
├── docker-compose.dev.yml       # Development services
└── Makefile                     # Common commands (make install, make dev, make test)
```

## Roadmap

### Completed
Transaction management, multi-provider bank sync (Plaid/Teller/MX), investment analysis (10 tabs incl. dividend income), retirement planner with Monte Carlo, FIRE planning, age-aware tax advisor, enhanced financial trends, multi-user households with RBAC, guest access, budget management, cash flow analytics, debt payoff strategies, subscription tracking, education planning, rental property P&L, rule engine, dark mode, IdP-agnostic auth, GDPR compliance, centralized financial constants, and more. See [docs/features.md](docs/features.md) for the full list.

## License

See [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

---

**Built with FastAPI, React, PostgreSQL, Redis, and Celery**
