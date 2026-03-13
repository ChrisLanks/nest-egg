# Features

Detailed feature documentation for Nest Egg. For a quick overview, see the [README](../README.md).

## Transaction & Account Management

- **Multi-Source Data Import** — providers are optional and can all run simultaneously:
  - **Plaid** (optional): Automatic bank sync with 11,000+ institutions worldwide — paid after free tier
  - **Teller** (optional): Automatic bank sync with 5,000+ US institutions — 100 free accounts/month
  - **MX** (optional): Enterprise bank data aggregation with 16,000+ institutions (US & Canada) — requires sales contract
  - **CSV Import**: Manual upload for unsupported banks or historical data
  - **Investment Data**: Yahoo Finance (free, unlimited), Finnhub (60/min free), or Alpha Vantage (25/day free)
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

## Smart Categorization & Labels

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

## Investment Analysis Dashboard

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

## Cash Flow Analytics (Income vs Expenses)

- **Advanced Drill-Down**: Click any stat or chart element to filter
- **Time Period Selection**: Month, Quarter, Year, YTD, Custom range
- **Group By Options**: Category, Label, or Month
- **Interactive Visualizations**:
  - Summary statistics (Total Income, Total Expenses, Net Savings, Savings Rate)
  - Category breakdown pie chart with clickable legends
  - Trend line chart showing income vs expenses over time
  - Detailed transaction drilldowns
- **Label-Based Analysis**: Filter by custom labels for specialized tracking

## Budget Management

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

## Smart Notification System

- **Real-Time Alerts**: Auto-refresh every 30 seconds
- **Notification Types**:
  - Budget alerts (exceeding thresholds)
  - Large transaction warnings
  - Account sync status
  - Low balance warnings
  - Cash flow forecast alerts (projected negative balances)
- **Notification Bell**: Unread count badge in top navigation
- **Mark as Read**: Individual or bulk "mark all read" functionality
- **Action Links**: Click notification to jump to relevant page
- **Email Delivery**: Automatic email notifications when SMTP is configured (per-user opt-in/out toggle in Preferences)

## Background Automation (Celery)

Scheduled tasks for hands-free operation:

- **Daily Budget Alerts** (Midnight): Check all budgets and create notifications
- **Weekly Recurring Detection** (Monday 2am): Auto-detect recurring transactions/subscriptions
- **Daily Cash Flow Forecast** (6:30am): Check for projected negative balances
- **Daily Data Retention** (3:30am): Purge transactions older than `DATA_RETENTION_DAYS` (disabled by default; dry-run safety)
- **Daily Portfolio Snapshots** (11:59pm): Capture end-of-day holdings values
  - Smart offset-based scheduling distributes load across 24 hours
  - Each organization runs at a consistent time based on UUID hash

## Multi-User Household Support

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

## RBAC Permission Grants

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

## Dark Mode

- **Three-Way Toggle**: Light, Dark, or System (follows OS preference) — configurable in Personal Settings
- **Semantic Color Tokens**: All 600+ color references use theme-aware tokens that auto-switch between light and dark palettes
- **Zero Flash**: `ColorModeScript` in `index.html` prevents white flash on page load in dark mode
- **Full Coverage**: Every page, modal, chart tooltip, and component supports both modes
- **Persistent Preference**: Stored in `localStorage` — survives sessions without backend changes

## IdP-Agnostic Authentication

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

## Manual Assets & Accounts

- **Manual Account Types**: Savings, Checking, Investment, Retirement, Loan, Mortgage, Credit Card, Other
- **Property Tracking**: Track real estate with address, mortgage balance, and equity calculation
- **Vehicle Tracking**: Track vehicles with VIN, mileage, loan balance, and equity calculation
- **Auto-Valuation**: Automatically refresh property and vehicle market values via third-party APIs
  - Property: RentCast (free), ATTOM (paid), or Zillow via RapidAPI (not recommended)
  - Vehicle: MarketCheck (VIN-based) + NHTSA VIN decode (always free)
  - Multiple providers: UI shows a selector when more than one key is configured
- **Valuation Adjustment**: User-defined percentage adjustment for property/vehicle valuations
- **Manual Balance Updates**: Update account balances directly
- **Investment Holdings**: Manually add stocks, ETFs, bonds, etc.
- **Plaid Holdings Sync**: Automatic investment holdings sync for Plaid-linked accounts
- **Account Provider Migration**: Switch accounts between providers (Plaid -> Manual, Teller -> Manual, etc.)
  - Two-step confirmation dialog on Account Detail page
  - Preserves all transactions, holdings, and contributions
  - Full migration audit log with history viewer
  - Reversible — migrate back to a linked provider later

## Predictive Features

- **Cash Flow Forecasting**: 30/60/90-day projections using recurring transaction patterns
- **Monte Carlo Simulations**: Investment growth modeling with uncertainty
- **Negative Balance Alerts**: Proactive warnings when forecast shows insufficient funds

## Retirement Planner

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

## FIRE Dashboard (Financial Independence, Retire Early)

Track your progress toward financial independence with real-time metrics:

- **FI Ratio**: How close your investable assets are to covering annual expenses indefinitely (at your chosen withdrawal rate)
- **Savings Rate**: Percentage of income you're saving, calculated from categorized transactions
- **Years to FI**: Estimated time until your investments can sustain your lifestyle, factoring in growth and savings
- **Coast FI**: Whether your current investments would grow to your FI number by retirement age — even without further contributions
- **Configurable Assumptions**: Adjust withdrawal rate (1-10%), expected return (0-20%), and retirement age (30-100)
- **Household Support**: View metrics for the combined household or filter by individual member
- **Empty Data Handling**: Graceful messaging when accounts/transactions haven't been set up yet — no misleading "FI Achieved" on zero data
- **Dashboard Widget**: Compact FIRE progress card available as a dashboard widget

## Capital Gains & Tax Lots

Track investment cost basis and capital gains for tax purposes:

- **Tax Lot Tracking**: Each share purchase creates a lot with acquisition date, quantity, and cost basis
- **Cost Basis Methods**: FIFO (First In, First Out), LIFO (Last In, First Out), or HIFO (Highest In, First Out)
- **Record Sales**: Log share sales with automatic lot matching and gain/loss calculation
- **Unrealized Gains**: Per-account summary of open positions with short-term vs long-term breakdown
- **Realized Gains**: Year-by-year view of closed positions with tax category breakdown
- **Import from Holdings**: Auto-create tax lots from existing holding cost basis data
- **Integrated in Account Detail**: Appears on investment account pages (brokerage, IRA, 401k, etc.)

## Transaction Attachments

Attach receipts, invoices, and documents to any transaction:

- **File Upload**: Drag-and-drop or click-to-upload, supporting images (JPEG, PNG, GIF, WebP) and PDF
- **Size Limits**: Max 10 MB per file, 5 attachments per transaction
- **Download**: View or download attachments from the transaction detail modal
- **Storage**: S3 (production) or local filesystem (development)
- **Permission-Aware**: Upload/delete only available for transactions you own

## Balance Reconciliation

Verify that bank-reported balances match locally computed balances:

- **Bank vs Computed**: Side-by-side comparison of the bank's reported balance and the sum of local transactions
- **Discrepancy Detection**: Color-coded status badges (Reconciled, Minor Discrepancy, Discrepancy Found)
- **Transaction Count**: Shows how many transactions are being reconciled
- **Sync Status**: Displays last sync timestamp
- **Auto-Display**: Only shown for bank-connected accounts (not manual accounts)

## Currency & Regional Settings

- **Default Currency**: Choose from 10 major currencies (USD, EUR, GBP, CAD, AUD, JPY, CHF, INR, CNY, BRL)
- **Per-User Setting**: Each household member can set their own default currency in Preferences
- **Inflation Adjustments**: Configurable per retirement scenario in the Retirement Planner

## Progressive Web App (PWA)

- **Installable**: Add to home screen on mobile and desktop
- **Offline Support**: Service worker with cache-first strategy for static assets, network-first for API calls
- **App Manifest**: Custom icons, theme color, and standalone display mode

## Circuit Breaker (Backend Resilience)

- **Automatic Failover**: External API calls (Plaid, Teller, MX, market data) wrapped in circuit breakers
- **Three States**: Closed (normal), Open (failing — returns cached/fallback), Half-Open (testing recovery)
- **Redis-Backed**: Circuit state shared across workers for consistent behavior
- **Graceful Degradation**: Falls back to in-memory state when Redis is unavailable

## Security Features

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
- **Anomaly Detection Middleware**: Request logging with structured fields for security monitoring; read-operation audit for sensitive endpoints
- **GDPR Compliance**: Right to erasure, data export (streaming ZIP), consent tracking, configurable data retention
- **Database Isolation**: Row-level security with organization-scoped queries
- **API Docs Disabled in Production**: Swagger/ReDoc/OpenAPI only available when `DEBUG=true`
- **Webhook Signature Verification**: Plaid and Teller webhooks verified before processing (HMAC-SHA256)
- **RBAC Audit Trail**: Immutable log of every permission grant change (actor, IP, before/after state)

## Data Integrity & Deduplication

### Guaranteed No Duplicates

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

### Cross-Provider Deduplication

When the same bank account is linked via multiple providers (e.g., Chase via Plaid **and** Teller **and** MX), deduplication prevents double-counting:

- **Account level**: SHA-256 hash of `institution_id + account_id` — first link becomes primary; duplicates flagged
- **Transaction level**: SHA-256 hash of `date + amount + merchant + account_id` + provider transaction IDs — same transaction from two sources stored once
- **Household level**: Same account added by two different household members -> only one copy in Combined view

## Scalability Safeguards

- **Date Range Validation**: Shared utility caps queries to ~50 years
- **Pagination Depth Caps**: OFFSET limited to 10,000 on report templates and audit log
- **Merchant GROUP BY Limits**: All unbounded merchant aggregation queries capped to 500 results
- **Real Health Check**: `/health` verifies actual DB connectivity and returns 503 when unreachable
- **Dashboard Query Consolidation**: Account data fetched once (eliminates 4 redundant queries)
- **Forecast O(n) Optimization**: Transaction-by-date pre-grouping replaces O(n*days) scan
