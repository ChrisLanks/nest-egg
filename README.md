# Nest Egg - Personal Finance Tracking Application

A comprehensive multi-user personal finance application for tracking transactions, investments, budgets, retirement planning, and cash flow analysis with smart automation and proactive notifications.

The real power in this tool, is the ability to invite others to your household (up to 5). Doing so will allow all cashflow trends, retirement data, debt planning, etc to be analyzed together allowing an accurate, single, holistic view. However, individual views are still accesable. You can change this in the top right corner of the page always. You can see the financial data of your personal account, and/or a significant other. The tool is also smart enough to de-duplicate the accounts. If you both have the mortgage or the same credit card, it will only show up once in the merged, combined household, view. 
In addition, a household member can grant permissions to other household members to specific tools, ensuring a household user's settings cannot be changed without permission. (See more detail below).


## Screenshots. 
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


## Views:

<img width="1512" height="861" alt="image" src="https://github.com/user-attachments/assets/9e6765e0-a777-4515-8826-3093040ab9fe" />

<img width="1512" height="860" alt="image" src="https://github.com/user-attachments/assets/d56f9f6f-03cb-4794-8a53-0680db50194a" />

<img width="1512" height="859" alt="image" src="https://github.com/user-attachments/assets/26e7aec8-f0de-4041-8820-65343b397d73" />

## Permissions:

<img width="1512" height="860" alt="image" src="https://github.com/user-attachments/assets/94fb5578-fb31-4aa9-8275-0d1fab99f75f" />

<img width="1512" height="861" alt="image" src="https://github.com/user-attachments/assets/dfc2cf4a-5095-40ff-97ae-02376c5f2442" />

<img width="454" height="590" alt="image" src="https://github.com/user-attachments/assets/f5396561-8d8e-4730-a1f5-48aa58437095" />


## ✨ Features

### 📊 **Transaction & Account Management**
- **Multi-Source Data Import** — providers are optional and can all run simultaneously:
  - 🏦 **Plaid** (optional): Automatic bank sync with 11,000+ institutions worldwide — paid after free tier
  - 🏦 **Teller** (optional): Automatic bank sync with 5,000+ US institutions — 100 free accounts/month
  - 🏦 **MX** (optional): Enterprise bank data aggregation with 16,000+ institutions (US & Canada) — requires sales contract
  - 📄 **CSV Import**: Manual upload for unsupported banks or historical data
  - 💰 **Investment Data**: Yahoo Finance (free, unlimited), Finnhub (60 calls/min free), or Alpha Vantage (25 calls/day free)
  - All providers can be active at the same time; the deduplication layer prevents double-counting
- **Smart Deduplication**: Multi-layer duplicate detection ensures no double-counting
  - Provider transaction IDs (Teller)
  - Content-based hashing (date + amount + merchant + account)
  - Database unique constraints
  - **Guaranteed**: Same transaction from multiple sources only counted once
- **Column Visibility**: Customize transaction table columns (Date, Merchant, Account, Category, Labels, Amount, Status)
- **Bulk Operations**: Edit multiple transactions at once (category, labels, mark as reviewed)
- **Advanced Filtering**: Search by merchant, category, account, labels, amount range
- **Shift-Click Selection**: Select multiple transactions in a range

### 🏷️ **Smart Categorization & Labels**
- **Custom Categories**: Create your own category hierarchy with custom colors
- **Automatic Category Mapping**: Teller provides categorized transactions, with automatic mapping to your custom categories
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
Comprehensive 9-tab portfolio analysis with **multi-provider** market data:
- **Real-Time Market Data**: Yahoo Finance (free, unlimited), Finnhub (60/min free), or Alpha Vantage (25/day free)
- **Asset Allocation**: Interactive treemap visualization with drill-down
- **Sector Breakdown**: Holdings by financial sector (Tech, Healthcare, Financials, etc.)
- **Future Growth**: Monte Carlo simulation with best/worst/median projections
  - Adjustable return rate, volatility, inflation, and time horizon
  - Inflation-adjusted and nominal value views
- **Performance Trends**: Historical tracking with CAGR and YoY growth
  - Time range selector (1M, 3M, 6M, 1Y, ALL)
  - Cost basis comparison
  - Real-time price updates on demand
- **Risk Analysis**: Volatility, diversification scores, and concentration warnings
  - Overall risk score (0-100) with color-coded badges
  - Asset class allocation breakdown
- **Holdings Detail**: Sortable table with CSV export
- **Roth Conversion Analyzer**: Model tax-efficient Roth conversion strategies
- **Tax-Loss Harvesting**: Identify unrealized losses, estimate tax savings (27% combined rate), wash-sale rule warnings, and same-sector replacement suggestions

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
- **Shared Budgets**: Share budgets with specific household members or the entire household

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
- **Email Delivery**: Automatic email notifications when SMTP is configured (per-user opt-in/out toggle in Preferences)
- **Test Endpoint**: `/api/v1/notifications/test` for testing (requires authentication)

### 📅 **Background Automation (Celery)**
Scheduled tasks for hands-free operation:
- **Daily Budget Alerts** (Midnight): Check all budgets and create notifications
- **Weekly Recurring Detection** (Monday 2am): Auto-detect recurring transactions/subscriptions
- **Daily Cash Flow Forecast** (6:30am): Check for projected negative balances
- **Daily Data Retention** (3:30am): Purge transactions older than `DATA_RETENTION_DAYS` (disabled by default; dry-run safety)
- **Daily Portfolio Snapshots** (11:59pm): Capture end-of-day holdings values
  - Smart offset-based scheduling distributes load across 24 hours
  - Each organization runs at a consistent time based on UUID hash

### 👥 **Multi-User Household Support**
- **Up to 5 Members**: Each with individual login credentials
- **View Modes**:
  - Combined Household: All accounts deduplicated
  - Individual: User's own accounts only
  - Other Members: View household members (with permission-controlled access)
- **Account Ownership**: Each user owns their connected accounts
- **Duplicate Detection**: Same bank account added by multiple users only counted once
  - Uses SHA256 hash of `institution_id + account_id`
  - Automatic on Teller sync
- **Deep Linking**: URL state preservation (`?user=<uuid>`)
- **RMD Calculations**: Age-specific Required Minimum Distribution per member

### 🔑 **RBAC Permission Grants**
Fine-grained access delegation between household members:
- **Default Read Access**: Household members always have implicit read access to each other's data — no grant needed
- **Write Grants**: Grant `create`, `update`, and/or `delete` access on top of the implicit read
- **Scope Options**: Grant one specific section (e.g. Transactions) or all sections at once via the "All Sections" toggle
- **Full Edit Preset**: One-click "Full Edit" button selects create+update+delete in the Grant Access dialog
- **Resource Types**: `account`, `transaction`, `bill`, `holding`, `budget`, `category`, `rule`, `savings_goal`, and more
- **Wildcard or Specific**: Grant access to all of a grantor's resources of a type, or to one specific resource by ID
- **Direct Grant**: Owner pushes access to grantee — no approval step needed
- **Expiry**: Optional `expires_at` date on any grant
- **Immutable Audit Log**: Every grant creation, update, and revocation is logged with actor, IP, and before/after state
- **`grant` is never delegatable**: Only the resource owner or an org admin can create/revoke grants — prevents privilege escalation
- **No implicit admin bypass**: Org admin status allows grant management (create/revoke) but does NOT grant implicit write access to other users' resources — cross-user editing is strictly grant-based end to end
- **Permissions Page**: `/permissions` — manage granted and received access with full audit history
- **Per-Page Guards**: Edit/Create/Delete buttons are hidden on every page when the viewer does not have write access for that specific resource type

### 🎨 **Dark Mode**
- **Three-Way Toggle**: Light, Dark, or System (follows OS preference) — configurable in Personal Settings
- **Semantic Color Tokens**: All 600+ color references use theme-aware tokens that auto-switch between light and dark palettes
- **Zero Flash**: `ColorModeScript` in `index.html` prevents white flash on page load in dark mode
- **Full Coverage**: Every page, modal, chart tooltip, and component supports both modes
- **Persistent Preference**: Stored in `localStorage` — survives sessions without backend changes

### 🔐 **IdP-Agnostic Authentication**
Drop-in support for external identity providers alongside the built-in JWT system:
- **Built-in (default)**: App's own HS256 JWT — works out of the box, no config needed
- **AWS Cognito**: Enable with `IDENTITY_PROVIDER_CHAIN=cognito,builtin` + `IDP_COGNITO_*` vars
- **Keycloak**: Enable with `IDENTITY_PROVIDER_CHAIN=keycloak,builtin` + `IDP_KEYCLOAK_*` vars
- **Okta**: Enable with `IDENTITY_PROVIDER_CHAIN=okta,builtin` + `IDP_OKTA_*` vars
- **Google**: Enable with `IDENTITY_PROVIDER_CHAIN=google,builtin` + `IDP_GOOGLE_CLIENT_ID`
- **Priority Chain**: Multiple providers active simultaneously; first JWT `iss` claim match wins
- **Auto-Provisioning**: First external login creates a User + Organization + UserConsent automatically
- **Group Sync**: IdP group membership synced on every login; maps to `is_org_admin` via configurable group name
- **JWKS Cache**: Public keys cached 1 hour (httpx async fetch with TTL)

### 🏠 **Manual Assets & Accounts**
- **Manual Account Types**: Savings, Checking, Investment, Retirement, Loan, Mortgage, Credit Card, Other
- **Property Tracking**: Track real estate with address, mortgage balance, and equity calculation
- **Vehicle Tracking**: Track vehicles with VIN, mileage, loan balance, and equity calculation
- **Auto-Valuation**: Automatically refresh property and vehicle market values via third-party APIs
  - Property: RentCast (free), ATTOM (paid), or Zillow via RapidAPI (not recommended, see below)
  - Vehicle: MarketCheck (VIN-based) + NHTSA VIN decode (always free)
  - Multiple providers: UI shows a selector when more than one key is configured
- **Valuation Adjustment**: User-defined percentage adjustment for property/vehicle valuations (e.g., negative for damage, positive for upgrades)
- **Manual Balance Updates**: Update account balances directly
- **Investment Holdings**: Manually add stocks, ETFs, bonds, etc.
- **Plaid Holdings Sync**: Automatic investment holdings sync for Plaid-linked accounts (`POST /plaid/sync-holdings/{account_id}`)
- **Account Provider Migration**: Switch accounts between providers (Plaid → Manual, Teller → Manual, etc.)
  - Two-step confirmation dialog on Account Detail page
  - Preserves all transactions, holdings, and contributions
  - Full migration audit log with history viewer
  - Reversible — migrate back to a linked provider later

### 🔮 **Predictive Features**
- **Cash Flow Forecasting**: 30/60/90-day projections using recurring transaction patterns
- **Monte Carlo Simulations**: Investment growth modeling with uncertainty
- **Negative Balance Alerts**: Proactive warnings when forecast shows insufficient funds

### 🏖️ **Retirement Planner**
Full retirement planning suite with Monte Carlo simulation, life event modeling, and household support:
- **Monte Carlo Fan Chart**: 1,000-run simulation with P10/P25/P50/P75/P90 percentile bands
- **Readiness Score**: 0-100 score with color-coded gauge showing retirement preparedness
- **Multiple Scenarios**: Create, duplicate, rename (double-click tab), and compare up to 3 scenarios side-by-side
- **Life Event Timeline**: Add preset events (child, home purchase, career change, elder care, etc.) or create custom events
  - Events automatically re-run simulation so the chart updates immediately
  - Visual timeline with edit and delete inline
- **Social Security Estimator**: Automatic PIA estimation from income, or manual override toggle with custom monthly amount
  - Claiming age slider (62-70) with benefit comparison at 62, FRA, and 70
- **Healthcare Cost Modeling**: Pre-65 insurance, Medicare (65+), and long-term care (85+) phases
  - Editable cost overrides per phase with pencil icon toggle
  - Medical inflation rate slider (0-15%)
  - IRMAA surcharge modeling based on retirement income
  - Optimistic display shows saved values immediately
- **Withdrawal Strategy Comparison**: Tax-optimized vs. simple rate strategies with clickable selection
  - "Better" badge highlights the more efficient strategy
- **Portfolio Summary**: Real-time breakdown by tax treatment (Pre-Tax, Roth, Taxable, HSA, Cash)
  - Individual account drill-down under each bucket
  - Editable tax rate assumptions (federal, state, capital gains)
  - Savings rate indicator with color-coded threshold
- **Scenario Settings Panel**: Adjustable sliders for retirement age (15-95), plan-through age, spending, returns, volatility, inflation, and withdrawal rate
- **Household View**: Per-member retirement plans with member filter in combined view
- **CSV Export**: Download projection data for external analysis
- **Smart Scroll**: Page loads at top; tab switching preserves scroll position

### 🔒 **Security Features**
- **Redis-Backed Rate Limiting**: 1000 req/min per user/IP — distributed sliding window (safe across multiple workers/instances)
- **CSRF Protection**: Double-submit cookie pattern with constant-time token comparison
- **Request Size Limiting**: 10 MB cap on request bodies (Content-Length + actual body verification)
- **Security Headers**: Strict CSP (no `unsafe-inline`/`unsafe-eval` in prod), HSTS, X-Frame-Options, X-XSS-Protection
- **Input Sanitization**: HTML tag stripping + entity escaping on all user text fields; ILIKE wildcard escaping for search
- **Encrypted PII**: VIN, property address/zip, annual salary encrypted at rest (Fernet AES-128-CBC)
- **Encrypted Credentials**: Plaid and Teller credentials encrypted at rest with AES-256; MX uses server-side Basic Auth (no stored token)
- **JWT Authentication**: Secure token-based auth with httpOnly-cookie refresh tokens and automatic rotation
- **Two-Factor Authentication (MFA)**: TOTP-based 2FA with backup codes; enforced at login in production
- **Account Lockout**: Configurable failed-attempt lockout (default 5 attempts / 30 min)
- **Anomaly Detection Middleware**: Request logging with structured fields for security monitoring; read-operation audit for sensitive endpoints (export, profile, portfolio)
- **GDPR Right to Erasure**: `DELETE /settings/account` — password-confirmed account deletion with cookie clearing
- **GDPR Records of Processing**: Admin-only `/monitoring/data-processing-activities` endpoint (Article 30 RoPA)
- **GDPR Data Export**: Streaming ZIP export with no row cap — batched 5K rows at a time for constant memory
- **Consent Tracking**: ToS and Privacy Policy acceptance recorded at registration with IP and version
- **Configurable Data Retention**: Optional `DATA_RETENTION_DAYS` with dry-run safety default; Celery task purges old transactions nightly
- **Database Isolation**: Row-level security with organization-scoped queries
- **API Docs Disabled in Production**: Swagger/ReDoc/OpenAPI only available when `DEBUG=true`
- **Production Config Validation**: `APP_BASE_URL` rejects `localhost` when `ENVIRONMENT=production`
- **Distributed Snapshot Scheduler**: Redis distributed lock prevents duplicate snapshot captures across instances
- **OIDC/OAuth2 Support**: RS256 token validation via JWKS for Cognito, Keycloak, Okta, and Google (see IdP-Agnostic Authentication above)
- **RBAC Audit Trail**: Immutable log of every permission grant change (actor, IP, before/after state)
- **Webhook Signature Verification**: Plaid and Teller webhooks verified before processing (HMAC-SHA256)
- **MX Sandbox Isolation**: MX defaults to disabled (`MX_ENABLED=false`) and uses sandbox endpoint (`int-api.mx.com`) for development

### **Scalability Safeguards**
- **Date Range Validation**: Shared utility caps queries to ~50 years; applied to dashboard, income/expenses, and holdings endpoints
- **Pagination Depth Caps**: OFFSET limited to 10,000 on report templates and audit log to prevent deep table scans
- **Merchant GROUP BY Limits**: All unbounded merchant aggregation queries capped to 500 results
- **Real Health Check**: `/health` verifies actual DB connectivity and returns 503 when unreachable (Docker/K8s will restart)
- **Dashboard Query Consolidation**: Account data fetched once (eliminates 4 redundant queries); spending + income merged into single `CASE WHEN` query
- **Forecast O(n) Optimization**: Transaction-by-date pre-grouping replaces O(n*days) scan
- **Insights Query Consolidation**: Two identical month-aggregation queries merged into one with `CASE WHEN`

## 🛡️ Data Integrity & Deduplication

### **Guaranteed No Duplicates**

The application uses a **multi-layer deduplication strategy** to ensure transactions are never double-counted:

#### Layer 1: Provider Transaction IDs
- Teller: Uses `id` from Teller API
- Database unique constraint on `(account_id, plaid_transaction_id)` (column name retained for compatibility)

#### Layer 2: Content-Based Hashing
- SHA256 hash of: `date + amount + merchant_name + account_id`
- Stored in `transaction_hash` column
- Database unique constraint prevents exact duplicates
- Works for CSV imports and manual entries

#### Layer 3: Household Account Deduplication
- SHA256 hash of: `institution_id + account_id` (works across Plaid and Teller)
- Stored in `plaid_item_hash` column (name retained for compatibility)
- When multiple users link the same bank account (via any provider):
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

#### Teller Sync (when `TELLER_ENABLED=true`)
```bash
# Automatic daily sync via Celery

# Manual sync via UI
Dashboard → Sync button on account card

# API endpoint
POST /api/v1/teller/sync-account/{account_id}
```

#### Plaid Sync (when `PLAID_ENABLED=true`)
```bash
# Automatic sync on configurable interval (PLAID_SYNC_INTERVAL_HOURS)

# Manual sync via UI
Dashboard → Sync button on account card

# API endpoint
POST /api/v1/plaid/sync/{account_id}
```

> Both providers can run at the same time. Accounts from both appear in the UI, deduplicated automatically.

#### Yahoo Finance (Investment Data)
```bash
# Automatic price refresh
# Provider: Yahoo Finance (free, unlimited)

# Manual refresh via UI
Investments → Refresh Prices button

# API endpoint
GET /api/v1/market-data/quote/{symbol}

# Configure market data provider in .env:
MARKET_DATA_PROVIDER=yahoo_finance  # Default provider
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

#### Property & Vehicle Auto-Valuation

Set one or more provider keys in `.env` to enable the "Refresh Valuation" button on property and vehicle accounts. No key = manual-only updates.

**Property providers** (pick one or more — UI shows a selector when multiple are configured):

| Provider | Key | Cost | Notes |
|---|---|---|---|
| **RentCast** ✅ | `RENTCAST_API_KEY` | Free (50 calls/month) | **Recommended.** Official API, permanent free tier. Sign up: [rentcast.io](https://app.rentcast.io/app/api-access) |
| ATTOM | `ATTOM_API_KEY` | Paid (30-day trial) | Sign up: [attomdata.com](https://api.gateway.attomdata.com) |
| Zillow ⚠️ | `ZILLOW_RAPIDAPI_KEY` | ~$10/month (RapidAPI) | **Not recommended.** Zillow's official API is MLS-partner-only. This uses an unofficial third-party scraper wrapper on RapidAPI (`zillow-com1.p.rapidapi.com`). May violate Zillow's Terms of Service. Sign up: [rapidapi.com/apimaker/api/zillow-com1](https://rapidapi.com/apimaker/api/zillow-com1) |

**Vehicle providers:**

| Provider | Key | Cost | Notes |
|---|---|---|---|
| MarketCheck | `MARKETCHECK_API_KEY` | Paid | VIN-based used-car valuations. Sign up: [marketcheck.com](https://www.marketcheck.com) |
| NHTSA | — | Free (always on) | VIN decode only (year/make/model, no price). No key needed. |

```bash
# .env example
RENTCAST_API_KEY=your_rentcast_key          # Recommended for property
ATTOM_API_KEY=your_attom_key               # Optional additional property provider
ZILLOW_RAPIDAPI_KEY=your_rapidapi_key      # Not recommended (unofficial wrapper)
MARKETCHECK_API_KEY=your_marketcheck_key   # For vehicle valuation
```

## 🚀 Technology Stack

### Backend
- **FastAPI** - Modern Python async web framework
- **PostgreSQL** - Primary database with JSONB support
- **Redis** - Caching, rate limiting, and Celery task queue
- **Celery** - Background task processing with Beat scheduler
- **SQLAlchemy 2.0** - Async ORM with relationship loading
- **Alembic** - Database migrations
- **Plaid API** - Financial institution integration (11,000+ banks worldwide)
- **Teller API** - Financial institution integration (5,000+ US banks, 100 free accounts/month)
- **MX Platform API** - Enterprise bank data aggregation (16,000+ institutions, US & Canada)
- **Yahoo Finance (yfinance)** - Free, unlimited investment data
- **Finnhub** - Market data with 60 free calls/min
- **Alpha Vantage** - Market data with 25 free calls/day
- **Pydantic v2** - Request/response validation
- **Passlib** - Password hashing with bcrypt
- **python-jose** - JWT token management
- **Cryptography** - AES-256 encryption for sensitive credentials
- **Prometheus** + **prometheus-fastapi-instrumentator** - Metrics and monitoring
- **Sentry SDK** - Error tracking and performance monitoring
- **pyotp** - TOTP-based multi-factor authentication
- **httpx** - Async JWKS fetching for external identity providers

### Frontend
- **React 18** - UI library with hooks
- **TypeScript** - Type safety and IDE support
- **Vite** - Lightning-fast build tool
- **Chakra UI** - Accessible component library with dark mode support
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
- **Banking providers are optional** — the app works without any of them (manual accounts + CSV import):
  - Plaid credentials ([sign up](https://plaid.com)) — 11,000+ institutions worldwide
  - Teller credentials ([sign up](https://teller.io/signup)) — 100 free accounts/month (US only)
  - MX credentials (enterprise — [contact sales](https://www.mx.com/products/platform-api)) — 16,000+ institutions (US & Canada)
  - All three can be enabled at the same time; set none to use manual entry only
- Yahoo Finance integration (free, no API key required), or Finnhub/Alpha Vantage with free API keys

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

   # Auth & Encryption
   SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
   MASTER_ENCRYPTION_KEY=your-encryption-key  # Generate with: openssl rand -hex 32

   # Market Data (always free, no key needed)
   MARKET_DATA_PROVIDER=yahoo_finance

   # Celery
   CELERY_BROKER_URL=redis://redis:6379/0
   CELERY_RESULT_BACKEND=redis://redis:6379/0

   # Banking (optional — omit all to use manual accounts + CSV only)
   # PLAID_CLIENT_ID=your_plaid_client_id    # plaid.com — 11,000+ institutions
   # PLAID_SECRET=your_plaid_secret
   # TELLER_APP_ID=your_teller_app_id        # teller.io — 100 free/month
   # TELLER_API_KEY=your_teller_api_key
   # MX_CLIENT_ID=your_mx_client_id          # mx.com — enterprise (sales contract)
   # MX_API_KEY=your_mx_api_key
   # MX_ENABLED=true
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
# Create database and role (must match DATABASE_URL in .env):
#   createdb nestegg
#   psql nestegg -c "CREATE ROLE nestegg WITH LOGIN PASSWORD 'nestegg_dev_password';"
#   psql nestegg -c "GRANT ALL PRIVILEGES ON DATABASE nestegg TO nestegg;"

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
- **API Docs (Swagger)**: http://localhost:8000/docs _(dev mode only — disabled in production)_
- **API Docs (ReDoc)**: http://localhost:8000/redoc _(dev mode only)_
- **Celery Flower**: http://localhost:5555

### First Time Setup

1. **Register an account**: http://localhost:5173/register
2. **Verify email** (if email configured, otherwise auto-verified in dev)
3. **Link bank account**: Dashboard → Connect Account → Teller Connect
4. **Wait for sync**: Transactions should appear within 1-2 minutes
5. **Add investments**: Manually add holdings or sync from Teller (if supported)
6. **Refresh prices**: Investments page → Refresh Prices (uses Yahoo Finance)
7. **Set up categories**: Categories page → Create custom categories
8. **Create budgets**: Budgets page → New Budget
9. **Test notifications**:
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

### Demo / Test Credentials

The app ships with seed scripts for local development. After running migrations:

**Primary test user** (`test@test.com`) — uses dummy Teller data, no real bank connection needed:
```bash
# From backend/ directory with venv active:
python scripts/seed_mock_data.py        # seed accounts + transactions
python scripts/seed_categories.py      # seed custom categories
python scripts/seed_investment_holdings.py  # seed investment holdings
```

**Secondary test user** (`test2@test.com`) — used for multi-user household testing:
```bash
# Run via Docker (uses the app's hash_password — always correct):
docker exec nestegg-dev-backend python3 -c "
import asyncio
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password
from app.models.user import User, Organization, UserConsent, ConsentType
from app.config import settings
from sqlalchemy import select

async def create():
    await init_db()
    async with AsyncSessionLocal() as db:
        if (await db.execute(select(User).where(User.email == 'test2@test.com'))).scalar_one_or_none():
            print('Already exists'); return
        org = Organization(name='Test2 Household')
        db.add(org); await db.flush()
        user = User(email='test2@test.com', password_hash=hash_password('test1234'),
                    organization_id=org.id, is_org_admin=True, is_active=True, email_verified=True)
        db.add(user); await db.flush()
        for ct in (ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY):
            db.add(UserConsent(user_id=user.id, consent_type=ct.value, version=settings.TERMS_VERSION))
        await db.commit(); print('Created test2@test.com')

asyncio.run(create())
"
```

| Email | Password | Role | Notes |
|-------|----------|------|-------|
| `test@test.com` | `test1234` | Org admin | Register via UI first, then run seed scripts |
| `test2@test.com` | `test1234` | Org admin | Created by seed script above; separate household |

> **Note**: `test2@test.com` exists in a **separate organization** from `test@test.com`. To test
> household sharing, log in as `test@test.com` → Household Settings → Invite Member → enter
> `test2@test.com`. After accepting, both users will be in the same household.

**Reset a test user's password** (if you changed it and forgot):
```bash
cd backend && python scripts/reset_test_password.py   # resets test@test.com to test1234
```

## 🔧 Configuration

### Environment Variables

All variables live in `backend/.env`. Variables marked **[required]** have no default and the app will not start without them. Everything else is optional with the defaults shown.

#### Application

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `staging`, or `production`. Controls lockout bypass, security middleware, and docs visibility. |
| `DEBUG` | `false` | Enables Swagger UI at `/docs`. Always `false` in production. |
| `APP_NAME` | `Nest Egg` | Name returned in API responses. |
| `APP_VERSION` | `1.0.0` | Version string returned in API responses. |

#### Database & Cache

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — **[required]** | PostgreSQL async URL, e.g. `postgresql+asyncpg://user:pass@localhost:5432/nestegg` |
| `DB_ECHO` | `false` | Log all SQL statements (very verbose — dev only). |
| `DB_POOL_SIZE` | `20` | SQLAlchemy connection pool size. |
| `DB_MAX_OVERFLOW` | `10` | Extra connections allowed above pool size. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL (rate limiting, Celery broker). |

#### Security & Encryption

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — **[required]** | JWT signing secret. Generate with `openssl rand -hex 32`. Min 32 chars enforced in production. |
| `MASTER_ENCRYPTION_KEY` | — **[required]** | AES-256 key for encrypting Plaid/Teller tokens at rest. Generate with `openssl rand -hex 32`. |
| `ALGORITHM` | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime (industry standard). |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime (stored as httpOnly cookie). |
| `ENCRYPTION_KEY_V1` | — | Previous encryption key, used only for decryption during key rotation. |
| `ENCRYPTION_CURRENT_VERSION` | `1` | Version tag written on new encrypted rows. Increment on key rotation. |
| `MAX_LOGIN_ATTEMPTS` | `5` | Failed logins before account lockout (skipped in `ENVIRONMENT=development`). |
| `ACCOUNT_LOCKOUT_MINUTES` | `30` | Lockout duration after too many failed login attempts. |
| `ALLOWED_HOSTS` | `["*"]` | Trusted host list (TrustedHostMiddleware). Must be specific domains in production. |
| `CORS_ORIGINS` | `["http://localhost:3000", "http://localhost:5173"]` | Allowed CORS origins. Set to your frontend domain in production. |
| `TERMS_VERSION` | `2026-02` | Current Terms of Service version. Bump when ToS/Privacy Policy changes — users are re-prompted. |

#### Banking: Teller *(optional)*

Teller provides 100 free linked accounts per month in production. All optional — set `TELLER_ENABLED=false` to disable.

| Variable | Default | Description |
|---|---|---|
| `TELLER_ENABLED` | `true` | Enable/disable Teller integration entirely. |
| `TELLER_APP_ID` | `""` | Your Teller application ID from teller.io. |
| `TELLER_API_KEY` | `""` | Teller API key. |
| `TELLER_ENV` | `sandbox` | `sandbox` or `production`. |
| `TELLER_WEBHOOK_SECRET` | `""` | Secret for verifying Teller webhook signatures. |
| `TELLER_CERT_PATH` | `""` | Path to Teller-issued mTLS certificate (`.pem`). Required for all API calls in production. |

#### Banking: Plaid *(optional)*

Plaid supports 11,000+ institutions. All optional — set `PLAID_ENABLED=false` to disable.

| Variable | Default | Description |
|---|---|---|
| `PLAID_ENABLED` | `true` | Enable/disable Plaid integration entirely. |
| `PLAID_CLIENT_ID` | `""` | Plaid client ID from plaid.com. |
| `PLAID_SECRET` | `""` | Plaid secret key. |
| `PLAID_ENV` | `sandbox` | `sandbox`, `development`, or `production`. |
| `PLAID_WEBHOOK_SECRET` | `""` | Secret for verifying Plaid webhook signatures. |
| `PLAID_SYNC_INTERVAL_HOURS` | `6` | How often Celery syncs Plaid accounts in the background. |
| `SYNC_INITIAL_DAYS` | `90` | Days of history to fetch on first account link. |
| `SYNC_INCREMENTAL_DAYS` | `7` | Days of history to fetch on subsequent syncs. |
| `SYNC_MAX_RETRIES` | `3` | Max retry attempts on sync failure. |
| `SYNC_RETRY_DELAY_SECONDS` | `300` | Delay between sync retries. |
| `MAX_MANUAL_SYNCS_PER_HOUR` | `1` | Rate limit on user-triggered manual syncs. |

#### Banking: MX *(optional — enterprise)*

MX provides 16,000+ institution coverage across US and Canada. Requires a sales contract for production access. Disabled by default.

| Variable | Default | Description |
|---|---|---|
| `MX_ENABLED` | `false` | Enable/disable MX integration. Must be explicitly enabled. |
| `MX_CLIENT_ID` | `""` | MX Platform API client ID. |
| `MX_API_KEY` | `""` | MX Platform API key. |
| `MX_ENV` | `sandbox` | `sandbox` or `production`. Sandbox: `int-api.mx.com`, Production: `api.mx.com`. |

#### Investment Price Data *(optional)*

| Variable | Default | Description |
|---|---|---|
| `MARKET_DATA_PROVIDER` | `yahoo_finance` | Default price provider. Options: `yahoo_finance`, `alpha_vantage`, `finnhub`. |
| `ALPHA_VANTAGE_API_KEY` | — | Alpha Vantage key. Free tier: 500 calls/day, 25/min. [Sign up](https://www.alphavantage.co/support/#api-key) |
| `FINNHUB_API_KEY` | — | Finnhub key. Free tier: 60 calls/min. [Sign up](https://finnhub.io/register) |
| `PRICE_REFRESH_COOLDOWN_HOURS` | `6` | Minimum hours between automatic holding price refreshes. |

#### Property Auto-Valuation *(optional)*

At least one key must be set to enable the "Refresh Valuation" button on property accounts.

| Variable | Default | Description |
|---|---|---|
| `RENTCAST_API_KEY` | — | RentCast API key. Free tier: 50 calls/month, no credit card. **Recommended.** [Sign up](https://app.rentcast.io/app/api-access) |
| `ATTOM_API_KEY` | — | ATTOM Data Solutions key. Paid, 30-day trial. |
| `ZILLOW_RAPIDAPI_KEY` | — | Unofficial Zillow wrapper via RapidAPI. ⚠️ May violate Zillow ToS. |

#### Vehicle Auto-Valuation *(optional)*

| Variable | Default | Description |
|---|---|---|
| `MARKETCHECK_API_KEY` | — | MarketCheck key for KBB-comparable used-car valuations by VIN. NHTSA VIN decode is always free and requires no key. |

#### Background Jobs (Celery)

| Variable | Default | Description |
|---|---|---|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery task broker URL. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery result store URL. |
| `RULE_APPLICATION_INTERVAL_HOURS` | `1` | How often Celery re-applies categorization rules to new transactions. |

#### Data Retention *(optional)*

| Variable | Default | Description |
|---|---|---|
| `DATA_RETENTION_DAYS` | — (indefinite) | Delete transactions older than this many days. Leave unset to keep all data forever. |
| `DATA_RETENTION_DRY_RUN` | `true` | When `true`, logs what would be deleted without actually deleting. Set to `false` to enable real purges. |

#### Email / SMTP *(optional)*

Emails (verification, password reset, notifications) are silently skipped when `SMTP_HOST` is unset.

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | — | SMTP server hostname, e.g. `smtp.gmail.com`. Leave unset to disable email. |
| `SMTP_PORT` | `587` | SMTP port. `587` for STARTTLS, `465` for SSL. |
| `SMTP_USERNAME` | — | SMTP login username. |
| `SMTP_PASSWORD` | — | SMTP login password (use app-specific password for Gmail). |
| `SMTP_FROM_EMAIL` | `noreply@nestegg.app` | Sender address shown in outbound emails. |
| `SMTP_FROM_NAME` | `Nest Egg` | Sender display name. |
| `SMTP_USE_TLS` | `true` | Use STARTTLS (`true` for port 587). Set `false` for direct SSL on port 465. |
| `APP_BASE_URL` | `http://localhost:5173` | Base URL for clickable links in emails. **Must be your public domain in production.** |

#### Observability & Monitoring

| Variable | Default | Description |
|---|---|---|
| `SENTRY_DSN` | — | Sentry DSN for error tracking. Leave unset to disable Sentry. |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `LOG_FORMAT` | `text` | Log format: `text` (dev) or `json` (production, for log aggregators). |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics endpoint. |
| `METRICS_ADMIN_PORT` | `9090` | Port for the Prometheus `/metrics` admin server (separate from the main API). |
| `METRICS_USERNAME` | `admin` | Basic auth username for the metrics endpoint. |
| `METRICS_PASSWORD` | `metrics_admin` | Basic auth password for the metrics endpoint. **Change in production.** |
| `METRICS_INCLUDE_IN_SCHEMA` | `false` | Show metrics endpoint in Swagger UI. |

#### Identity Provider Chain *(optional)*

By default the app uses its own HS256 JWT (`builtin`). Add external providers to enable SSO without replacing built-in auth.

| Variable | Default | Description |
|---|---|---|
| `IDENTITY_PROVIDER_CHAIN` | `builtin` | Ordered comma-separated list of active providers. First JWT `iss` match wins. E.g. `cognito,builtin`. |
| `IDP_COGNITO_ISSUER` | — | Cognito pool issuer URL: `https://cognito-idp.{region}.amazonaws.com/{pool-id}` |
| `IDP_COGNITO_CLIENT_ID` | — | Cognito app client ID. |
| `IDP_COGNITO_ADMIN_GROUP` | `nest-egg-admins` | Cognito group that grants `is_org_admin`. |
| `IDP_KEYCLOAK_ISSUER` | — | Keycloak realm URL: `https://keycloak.example.com/realms/{realm}` |
| `IDP_KEYCLOAK_CLIENT_ID` | — | Keycloak client ID. |
| `IDP_KEYCLOAK_ADMIN_GROUP` | `nest-egg-admins` | Keycloak group that grants `is_org_admin`. |
| `IDP_KEYCLOAK_GROUPS_CLAIM` | `groups` | JWT claim containing group memberships. |
| `IDP_OKTA_ISSUER` | — | Okta authorization server URL: `https://company.okta.com/oauth2/default` |
| `IDP_OKTA_CLIENT_ID` | — | Okta client ID. |
| `IDP_OKTA_GROUPS_CLAIM` | `groups` | JWT claim containing group memberships. |
| `IDP_GOOGLE_CLIENT_ID` | — | Google OAuth2 client ID (validates `aud` claim). Google does not expose group memberships. |

#### File Storage *(optional)*

| Variable | Default | Description |
|---|---|---|
| `STORAGE_BACKEND` | `local` | `local` (disk) or `s3` (AWS S3). |
| `LOCAL_UPLOAD_DIR` | `/tmp/nestegg-uploads` | Local directory for CSV uploads and attachments. Override in production. |
| `AWS_S3_BUCKET` | — | S3 bucket name (required when `STORAGE_BACKEND=s3`). |
| `AWS_REGION` | `us-east-1` | AWS region. |
| `AWS_ACCESS_KEY_ID` | — | AWS credentials. Omit to use IAM instance role. |
| `AWS_SECRET_ACCESS_KEY` | — | AWS credentials. Omit to use IAM instance role. |
| `AWS_S3_PREFIX` | `csv-uploads/` | Key prefix for S3 uploads. |

#### Pagination

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_PAGE_SIZE` | `50` | Default number of items per page in list endpoints. |
| `MAX_PAGE_SIZE` | `200` | Maximum items per page allowed by list endpoints. |

#### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000   # Backend URL (dev only — prod uses relative /api path)
VITE_APP_NAME=Nest Egg               # App name shown in browser tab
```

## 🏦 Banking Providers

All banking providers are **optional** and can be **enabled simultaneously**. The deduplication layer ensures accounts from multiple providers are never double-counted.

### Provider Comparison

| Feature | Plaid | Teller | MX | Manual / CSV |
|---------|-------|--------|-----|--------------|
| **Institution Coverage** | 11,000+ (US + int'l) | 5,000+ (US only) | 16,000+ (US & Canada) | Any |
| **Cost** | Paid after free tier | 100 free accounts/month | Enterprise (sales contract) | Free |
| **Transaction Categorization** | ✅ 350+ categories | ✅ Smart categorization | ✅ Categorized | Manual |
| **Investment Accounts** | ✅ Holdings sync | ⚠️ Manual tracking | ⚠️ Manual tracking | Manual |
| **Credit Cards** | ✅ | ✅ | ✅ | ✅ |
| **Auto Balance Updates** | ✅ | ✅ | ✅ | Manual |
| **Credentials Encrypted** | ✅ AES-256 at rest | ✅ AES-256 at rest | ✅ (no stored token) | N/A |

### Enabling Providers

Each provider is independently toggled via `.env`. Set **all three** to run them side-by-side:

```env
# Plaid (optional — comment out to disable)
PLAID_ENABLED=true
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=sandbox          # sandbox | development | production

# Teller (optional — comment out to disable)
TELLER_ENABLED=true
TELLER_APP_ID=your_teller_app_id
TELLER_API_KEY=your_teller_api_key
TELLER_ENV=sandbox         # sandbox | production
TELLER_CERT_PATH=/path/to/teller_cert.pem   # required for API calls

# MX (optional — enterprise only, disabled by default)
MX_ENABLED=true
MX_CLIENT_ID=your_mx_client_id
MX_API_KEY=your_mx_api_key
MX_ENV=sandbox             # sandbox | production

# Investment prices (always free)
MARKET_DATA_PROVIDER=yahoo_finance   # or: finnhub, alpha_vantage
# FINNHUB_API_KEY=your_finnhub_key   # 60 calls/min free
# ALPHA_VANTAGE_API_KEY=your_av_key  # 25 calls/day free
```

When multiple providers are enabled, users see a provider picker in the "Connect Account" flow. Existing data from any provider is always preserved — switching or adding providers is purely additive.

### Cross-Provider Deduplication

When the same bank account is linked via multiple providers (e.g., Chase via Plaid **and** Teller **and** MX), deduplication prevents double-counting:

- **Account level**: SHA-256 hash of `institution_id + account_id` (`plaid_item_hash`) — first link becomes primary; duplicates flagged
- **Transaction level**: SHA-256 hash of `date + amount + merchant + account_id` (`transaction_hash`) + provider transaction IDs — same transaction from two sources stored once
- **Household level**: Same account added by two different household members → only one copy in Combined view

```sql
-- Database constraints that enforce this
UNIQUE (account_id, plaid_transaction_id)
UNIQUE (transaction_hash) WHERE transaction_hash IS NOT NULL
UNIQUE (plaid_item_hash)  WHERE plaid_item_hash IS NOT NULL
```

### Verifying the Setup

```bash
# Check which providers the API has enabled
curl http://localhost:8000/api/v1/accounts/providers \
  -H "Authorization: Bearer <token>"

# Test investment data (always works, no provider key needed)
curl "http://localhost:8000/api/v1/market-data/quote/AAPL" \
  -H "Authorization: Bearer <token>"
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

#### 4. **Teller Sync Failing**

**Symptoms**: "Sync failed" error, old transactions

**Solutions**:
```bash
# Check Teller logs
docker-compose logs api | grep -i teller

# Verify Teller credentials
echo $TELLER_APP_ID
echo $TELLER_ENVIRONMENT

# Test Teller connection
curl -X GET http://localhost:8000/api/v1/teller/test-connection \
  -H "Authorization: Bearer <your-token>"

# Re-link account
Dashboard → Account → "Re-link Account" button
```

#### 5. **Yahoo Finance Price Fetch Failing**

**Symptoms**: "Failed to fetch quote" errors, stale prices

**Solutions**:
```bash
# Check market data logs
docker-compose logs api | grep -i yahoo

# Test Yahoo Finance manually
curl -X GET "http://localhost:8000/api/v1/market-data/quote/AAPL" \
  -H "Authorization: Bearer <your-token>"

# Verify rate limiting not hit (1000 req/min per user)
# Check response headers: X-RateLimit-Remaining

# Check symbol validity
# Yahoo Finance uses standard symbols: AAPL, GOOGL, SPY, etc.
```

#### 6. **Database Migration Issues**

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

#### 7. **Frontend Not Loading**

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
- [ ] Set `APP_BASE_URL=https://your-domain.com` (used in email verification / password-reset links)
- [ ] Configure HTTPS/SSL certificates
- [ ] Set restrictive `CORS_ORIGINS` and `ALLOWED_HOSTS`
- [ ] Use `nginx.prod.conf` for the frontend (passed automatically via `docker-compose.yml` build arg — strict CSP, HSTS)
- [ ] Ensure Redis is running — required for distributed rate limiting and snapshot scheduler lock
- [ ] Set up Sentry error tracking (`SENTRY_DSN`)

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
- [ ] Configure production Teller credentials (100 free accounts/month)
- [ ] Set up webhook URLs with HTTPS (if using Teller webhooks)
- [ ] Configure email service (SendGrid, Mailgun, SES)
- [ ] Set up monitoring (Datadog, New Relic, CloudWatch)
- [ ] Configure logging aggregation (Loggly, Papertrail)
- [ ] Verify Yahoo Finance access (no API key required)

#### Performance
- [ ] Enable HTTP/2
- [ ] Configure CDN for static assets
- [ ] Set up database indexes
- [ ] Enable query caching
- [ ] Configure Redis caching

### Docker Production Build

```bash
# Build production images
docker-compose build

# Run migrations
docker-compose run api alembic upgrade head

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Environment-Specific Settings

#### Production
```env
ENVIRONMENT=production
DEBUG=false
APP_BASE_URL=https://app.nestegg.com
ALLOWED_ORIGINS=https://app.nestegg.com
ALLOWED_HOSTS=app.nestegg.com,api.nestegg.com
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/nestegg
REDIS_URL=redis://prod-redis:6379/0
TELLER_ENVIRONMENT=production
MARKET_DATA_PROVIDER=yahoo_finance
```

#### Staging
```env
ENVIRONMENT=staging
DEBUG=false
ALLOWED_ORIGINS=https://staging.nestegg.com
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/nestegg
REDIS_URL=redis://staging-redis:6379/0
TELLER_ENVIRONMENT=sandbox
MARKET_DATA_PROVIDER=yahoo_finance
```

## 📝 Project Structure

```
nest-egg/
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── api/                  # API endpoints
│   │   │   └── v1/               # API version 1
│   │   │       ├── accounts.py           # Account management
│   │   │       ├── auth.py               # Authentication + MFA
│   │   │       ├── bank_linking.py       # Unified bank linking (Plaid + Teller + MX)
│   │   │       ├── bills.py              # Bills & recurring transactions
│   │   │       ├── budgets.py            # Budget CRUD
│   │   │       ├── categories.py         # Category management
│   │   │       ├── contributions.py      # Contribution tracking
│   │   │       ├── csv_import.py         # CSV import endpoint
│   │   │       ├── dashboard.py          # Dashboard stats & widgets
│   │   │       ├── debt_payoff.py        # Debt payoff planner
│   │   │       ├── holdings.py           # Investment holdings
│   │   │       ├── household.py          # Multi-user management
│   │   │       ├── income_expenses.py    # Cash flow analytics
│   │   │       ├── labels.py             # Label management
│   │   │       ├── market_data.py        # Yahoo Finance integration
│   │   │       ├── monitoring.py         # Health checks, rate-limit dashboard, GDPR RoPA
│   │   │       ├── notifications.py      # Notification CRUD
│   │   │       ├── plaid.py              # Plaid integration
│   │   │       ├── reports.py            # Custom reports builder
│   │   │       ├── rules.py              # Rule engine
│   │   │       ├── savings_goals.py      # Savings goals
│   │   │       ├── settings.py           # User settings, data export, account deletion
│   │   │       ├── subscriptions.py      # Subscription tracker
│   │   │       ├── teller.py             # Teller integration
│   │   │       ├── transaction_merges.py # Transaction merge/split
│   │   │       ├── transaction_splits.py # Transaction splits
│   │   │       └── transactions.py       # Transaction CRUD + CSV export
│   │   ├── core/                 # Core utilities
│   │   │   ├── config.py                 # Settings management
│   │   │   ├── database.py               # DB connection pool
│   │   │   ├── security.py               # Auth utilities
│   │   │   └── encryption.py             # Field encryption
│   │   ├── middleware/            # ASGI middleware
│   │   │   ├── csrf_protection.py        # Double-submit CSRF tokens
│   │   │   ├── rate_limit.py             # Global async rate limiter
│   │   │   ├── request_size_limit.py     # Body size enforcement
│   │   │   └── security_headers.py       # CSP, HSTS, X-Frame-Options
│   │   ├── models/               # SQLAlchemy models
│   │   │   ├── account.py                # Account + PlaidItem + TellerEnrollment + MxMember
│   │   │   ├── transaction.py            # Transaction + Label + Category
│   │   │   ├── budget.py                 # Budget model
│   │   │   ├── contribution.py           # Contribution tracking
│   │   │   ├── holding.py               # Holdings + portfolio snapshots
│   │   │   ├── mfa.py                    # UserMFA (TOTP)
│   │   │   ├── notification.py           # Notification model
│   │   │   ├── permission.py             # PermissionGrant + audit log
│   │   │   ├── recurring_transaction.py  # Recurring transaction patterns
│   │   │   ├── report_template.py        # Custom report templates
│   │   │   ├── transaction_merge.py      # Transaction merge records
│   │   │   ├── user.py                   # User + Organization + Invitation
│   │   │   ├── identity.py               # UserIdentity (IdP links)
│   │   │   └── ...                       # Other models
│   │   ├── schemas/              # Pydantic schemas
│   │   │   ├── account.py                # Account DTOs
│   │   │   ├── transaction.py            # Transaction DTOs
│   │   │   ├── permission.py             # Permission grant/audit DTOs
│   │   │   └── ...                       # Other schemas
│   │   ├── services/             # Business logic
│   │   │   ├── budget_service.py         # Budget calculations
│   │   │   ├── deduplication_service.py  # Duplicate detection
│   │   │   ├── notification_service.py   # Notification creation
│   │   │   ├── teller_service.py         # Teller sync logic
│   │   │   ├── mx_service.py            # MX Platform API integration
│   │   │   ├── plaid_service.py         # Plaid SDK integration
│   │   │   ├── rule_engine_service.py    # Rule evaluation
│   │   │   ├── account_migration_service.py # Provider migration logic
│   │   │   ├── permission_service.py     # RBAC grant/check/revoke
│   │   │   ├── identity/                 # IdP provider chain
│   │   │   │   ├── base.py               # AuthenticatedIdentity + abstract provider
│   │   │   │   ├── builtin.py            # Built-in HS256 JWT provider
│   │   │   │   ├── oidc.py               # Generic OIDC (Cognito/Keycloak/Okta/Google)
│   │   │   │   └── chain.py              # IdentityProviderChain + build_chain()
│   │   │   ├── market_data/              # Market data providers
│   │   │   │   ├── base_provider.py      # Abstract provider
│   │   │   │   ├── yahoo_finance_provider.py  # Yahoo Finance impl
│   │   │   │   ├── finnhub_provider.py        # Finnhub impl (60/min free)
│   │   │   │   ├── alpha_vantage_provider.py  # Alpha Vantage impl (25/day free)
│   │   │   │   └── provider_factory.py        # Provider factory + caching
│   │   │   └── ...                       # Other services
│   │   ├── workers/              # Celery tasks
│   │   │   ├── celery_app.py             # Celery configuration
│   │   │   └── tasks/                    # Task modules
│   │   │       ├── auth_tasks.py         # Token cleanup
│   │   │       ├── budget_tasks.py       # Budget alert tasks
│   │   │       ├── forecast_tasks.py     # Cash flow forecast
│   │   │       ├── holdings_tasks.py     # Price refresh
│   │   │       ├── interest_accrual_tasks.py  # Interest accrual
│   │   │       ├── recurring_tasks.py    # Pattern detection
│   │   │       ├── retention_tasks.py   # Data retention purge
│   │   │       └── snapshot_tasks.py     # Portfolio snapshots
│   │   ├── utils/                # Utility functions
│   │   │   └── date_validation.py       # Shared date range validation
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
│   │   │   ├── permissions/      # RBAC grant management UI
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
├── docker-compose.yml            # Production services
├── docker-compose.dev.yml        # Development overrides
├── Makefile                      # Common commands (make install, make dev, make test)
├── setup.sh                      # Automated first-time setup script
├── SELF_HOSTING.md               # Enterprise self-hosting guide
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

### Grant Data Access to a Household Member

```bash
# Via UI (recommended)
# 1. Login as the data owner
# 2. Navigate to /permissions (user menu → Permissions)
# 3. Click "Grant Access"
# 4. Pick member, resource type, and actions (read/create/update/delete)
# 5. Optionally set an expiry date

# Via API
curl -X POST http://localhost:8000/api/v1/permissions/grants \
  -H "Authorization: Bearer <owner-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "grantee_id": "<member-uuid>",
    "resource_type": "transaction",
    "actions": ["read", "update"]
  }'

# List what you have shared
curl -X GET http://localhost:8000/api/v1/permissions/given \
  -H "Authorization: Bearer <token>"

# Revoke a grant
curl -X DELETE http://localhost:8000/api/v1/permissions/grants/<grant-id> \
  -H "Authorization: Bearer <token>"
```

### Manually Sync Teller Account

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/teller/sync-account/<account-id> \
  -H "Authorization: Bearer <token>"

# Via Celery task
docker-compose exec celery_worker python -c "
from app.workers.tasks.teller_tasks import sync_account_task
sync_account_task.delay('<account-uuid>')
"
```

### Refresh Investment Prices

```bash
# Via API - Single quote
curl -X GET "http://localhost:8000/api/v1/market-data/quote/AAPL" \
  -H "Authorization: Bearer <token>"

# Via API - Batch quotes
curl -X POST "http://localhost:8000/api/v1/market-data/quote/batch" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '["AAPL", "GOOGL", "MSFT"]'

# Via API - Historical prices
curl -X GET "http://localhost:8000/api/v1/market-data/historical/AAPL?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <token>"
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

### 3. **Teller Sandbox Limitations**

When using Teller Sandbox environment:

- ⚠️ Test institutions only (test bank accounts)
- ⚠️ Limited transaction history in test mode
- ⚠️ No real-time updates (manual sync required)
- ✅ Switch to Production for real banks (100 free accounts/month)
- ✅ More generous limits than legacy providers

### 4. **Transaction Dedupe Only Within Organization**

Deduplication is **organization-scoped**:

- ✅ Same transaction imported twice → Deduped
- ✅ Same bank account added by household members → Deduped
- ❌ Same transaction across different organizations → Both kept (correct behavior)

### 5. **Category Mapping Persistence**

When you map a provider category to a custom category:

- Mapping stored in `category_mappings` table
- Applies to **all future transactions** from Teller
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

### 7. **Multi-User Permission Model**

There are two layers of permissions in the household:

**View mode** (top-of-page toggle):
- **Combined View**: Shows all household accounts (deduplicated)
- **Individual View**: Shows user's own accounts only

**RBAC grants** (`/permissions` page):
- **Implicit read**: All household members always have read access to each other's data — no explicit grant required
- Use the Permissions page to grant additional write access (`create`, `update`, `delete`) to specific resource types (accounts, transactions, bills, holdings, budgets, goals, rules, categories, etc.)
- **All Sections** scope: grant the same write permissions across every resource type in one operation
- **Full Edit** preset: instantly selects create+update+delete without checking each box manually
- Edit/delete/create buttons on each page are disabled when the viewer lacks write access for that resource type — including Combined Household view, where per-resource ownership is checked against grants
- Grants are per-action and can target all resources of a type or a specific resource by ID
- Only the resource owner or an org admin can create/revoke grants (admin status does NOT bypass resource access checks)
- All grant changes are recorded in an immutable audit log

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
- [x] **Teller integration** with automatic sync (100 free accounts/month)
- [x] **Yahoo Finance integration** for free, unlimited investment data
- [x] **Redis-backed distributed rate limiting** (1000 req/min per user/IP, works across multiple workers; falls back to in-memory in dev)
- [x] **Strict security headers in production** (CSP without `unsafe-inline`/`unsafe-eval`, HSTS — served via `nginx.prod.conf`)
- [x] Multi-user household support with deduplication
- [x] Transaction management with bulk operations
- [x] Rule engine for automated categorization
- [x] Custom categories with provider mapping
- [x] Label system for flexible tagging
- [x] Budget management with alerts
- [x] Notification system with real-time updates
- [x] Investment tracking with 9-tab analysis (including Tax-Loss Harvesting and Roth Conversion)
- [x] Cash flow analytics with drill-down
- [x] Tax-deductible transaction tracking
- [x] CSV import with deduplication
- [x] Smart portfolio snapshot scheduler with Redis distributed lock (safe for multi-instance deployments)
- [x] Celery background tasks
- [x] **RBAC permission grants** — per-action (read/create/update/delete), per-resource, with immutable audit log
- [x] **IdP-agnostic authentication** — pluggable Cognito, Keycloak, Okta, Google OIDC alongside built-in JWT
- [x] **Bill tracking** with ON_DEMAND frequency, labels, archiving, and merchant autocomplete
- [x] **Emergency fund template**, **401k match calculator**, **net worth projection**, **bill calendar**
- [x] **Data export** (ZIP with Mint-compatible CSV, full account data, tax reports)
- [x] **Roth conversion analyzer**
- [x] **Debt payoff planner** — snowball and avalanche strategies with amortization schedules
- [x] **Custom reports builder** — configurable templates with saved report definitions
- [x] **Multi-year trend analysis** — year-over-year comparisons and historical trends
- [x] **Subscription tracker** — automatic detection and management of recurring subscriptions
- [x] **Savings goals** — target-based savings tracking with progress visualization
- [x] **Transaction splits & merges** — split single transactions or merge duplicates
- [x] **Contributions tracking** — 401k, IRA, and other contribution tracking
- [x] **Dashboard widgets** — 14 configurable widgets (net worth, spending, budgets, goals, etc.)
- [x] **Interest accrual** — automated interest calculations for savings and debt accounts
- [x] **CSRF protection** — double-submit cookie pattern with constant-time comparison
- [x] **GDPR compliance** — Article 30 RoPA, data export (Article 20), right to erasure (Article 17)
- [x] **Enterprise hardening** — scalability safeguards (date range, pagination, merchant caps), streaming export, data retention, real health checks
- [x] **Performance optimization** — dashboard query consolidation (9 queries → 5), O(n) forecast, single-query insights
- [x] **Self-hosting documentation** — production checklist, backup/restore, scaling, encryption rotation (see `SELF_HOSTING.md`)
- [x] **Dark mode** — Light/Dark/System toggle with semantic color tokens across all 90+ components; zero-flash page load
- [x] **Clean TypeScript build** — all 125 pre-existing TS errors resolved; strict-mode clean `npm run build`
- [x] **Grant-based permission enforcement** — cross-user editing strictly governed by explicit grants (no org admin bypass); works correctly in Combined Household, Other-User, and Self views
- [x] **Shared/collaborative budgets & goals** — share budgets and savings goals with specific household members or the entire household
- [x] **Email notification delivery** — automatic email dispatch when SMTP is configured; per-user opt-in/out toggle
- [x] **Plaid investment holdings sync** — pull holdings from Plaid-linked investment accounts
- [x] **Tax-loss harvesting** — identify unrealized losses, estimate tax savings, wash-sale warnings, sector-based replacement suggestions
- [x] **Valuation adjustment** — user-defined percentage adjustment for property and vehicle auto-valuations
- [x] **Full Plaid API implementation** — real plaid-python SDK calls replacing stubs (link token, exchange, accounts sync)
- [x] **Finnhub market data provider** — 60 free calls/min with quote, historical, search, and holding metadata
- [x] **Alpha Vantage market data provider** — 25 free calls/day fallback with daily/weekly/monthly OHLCV
- [x] **MX Platform integration** — enterprise bank aggregation with httpx (16,000+ institutions, account & transaction sync)
- [x] **Market data provider factory** — pluggable provider system with caching, auto-fallback to Yahoo Finance
- [x] **Account provider migration** — switch accounts between providers (Plaid/Teller/MX/Manual) with two-step confirmation, full audit log, and migration history UI

### 🚧 In Progress
- [ ] Mobile app (React Native)

### 🔮 Future Features

- [ ] Receipt OCR and attachment storage
- [ ] Advanced investment analytics (Sharpe ratio, alpha, beta)
- [ ] Tax bracket optimization
- [ ] White-label SaaS offering

## 🐛 Recent Bug Fixes

### Combined Household View Permissions (Fixed)
- **Issue**: Users in Combined Household view could not edit other members' resources even when explicit write grants existed; conversely, org admins could edit without any grants
- **Root Cause**: (1) Permission grants were only fetched in other-user view, never in combined view; (2) Five frontend components used ownership-only checks instead of the grant system; (3) Both frontend and backend had an `is_org_admin` bypass that short-circuited grant checks
- **Fix**: Fetch grants in all non-self views, added `canWriteOwnedResource()` for per-resource grant-aware checks, removed org admin bypass from both frontend and backend permission services — cross-user editing is now strictly grant-based end to end

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
- **Plaid** - Financial data aggregation (11,000+ institutions)
- **Teller** - Financial data aggregation (100 free accounts/month)
- **MX** - Enterprise financial data aggregation (16,000+ institutions)
- **Yahoo Finance (yfinance)** - Free, unlimited investment data
- **Finnhub** - Market data (60 free calls/min)
- **Alpha Vantage** - Market data (25 free calls/day)
- **Celery** - Task queue
- **PostgreSQL** - Database
- **Redis** - Caching
- **SQLAlchemy** - ORM
- **Recharts** - Data visualization

---

**Built with ❤️ for personal finance management**

_Last Updated: February 2026 - Full Plaid/MX/Teller/Finnhub/Alpha Vantage provider integrations, shared budgets/goals, email notifications, tax-loss harvesting, dark mode, enterprise hardening, and 20+ new features!_
