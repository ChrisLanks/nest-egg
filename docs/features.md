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
  - **Auto-Provider Selection**: When adding an account, the app automatically selects the best configured provider (Plaid → Teller → MX priority); a toggle in the Add Account dialog lets users override and choose manually. Selection persists in browser storage. Falls back to manual entry when no provider is configured.
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

Comprehensive 11-tab portfolio analysis with **multi-provider** market data:

- **Real-Time Market Data**: Yahoo Finance (free, unlimited), Finnhub (60/min free), or Alpha Vantage (25/day free)
- **Asset Allocation**: Interactive treemap visualization with drill-down
- **Sector Breakdown**: Holdings by financial sector (Tech, Healthcare, Financials, etc.)
- **Future Growth**: Monte Carlo simulation with best/worst/median projections
  - Adjustable return rate, volatility, inflation, and time horizon
  - Inflation-adjusted and nominal value views
  - Default years calculated as `65 - birth_year` when available, else 10 years
  - Settings (years, return rate, volatility) persist across page refreshes via localStorage
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
- **Dividend Income**: Track dividend and investment income with summary stats, monthly chart, and top payers table (see Dividend & Investment Income section below)
- **Account Exclusion Tooltip**: Explains why primary residence and vehicles are excluded by default (needed to live in/use; investment properties count)
- **Trump Account Support**: Available as a manual investment account type

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
- **Money Flow Sankey Diagram**: Defaults to visible; collapsed/expanded state persists via localStorage

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

## Per-User Historical Snapshots

Net worth history filtered by household member:

- **Per-User Snapshots**: Daily snapshot task captures both household-level and per-user portfolio snapshots
- **Dashboard Integration**: Net Worth Over Time, Spending Insights, Cash Flow Forecast, and Financial Health widgets all update when switching user view
- **API Support**: `user_id` query parameter on `/holdings/snapshots` endpoint with household member verification
- **Partial Unique Indexes**: One household snapshot and one per-user snapshot per org per day, enforced at the database level

## Customizable Navigation Visibility

Per-user control over which tabs and sub-tabs appear in the navigation:

- **Per-Item Toggle**: Show or hide individual nav items from Preferences page
- **Account-Based Defaults**: Debt Payoff, Rental Properties, and Education tabs auto-hide when no relevant accounts exist
- **User Override**: Manually force-show or force-hide any item, overriding the account-based default
- **Reset to Default**: One-click reset clears all overrides and returns to auto-hide behavior
- **Per-User Storage**: Preferences stored in localStorage, independent per logged-in user
- **Conditional Permissions**: "My Permissions" menu item only appears for multi-member households

## Smart Notification System

- **Real-Time Alerts**: Auto-refresh every 120 seconds (pauses when tab is unfocused)
- **Notification Types**:
  - Budget alerts (exceeding thresholds)
  - Large transaction warnings
  - Account sync status (failures, re-auth required, stale accounts)
  - Account activity (new connections, duplicate detection)
  - Milestone events (net worth all-time highs, FIRE milestones)
  - Household events (member joins/leaves, retirement scenario updates)
  - Cash flow forecast alerts (projected negative balances)
- **Notification Bell**: Unread count badge in top navigation
- **Mark as Read**: Individual or bulk "mark all read" functionality
- **Action Links**: Click notification to jump to relevant page
- **Email Delivery**: Automatic email notifications when SMTP is configured (per-user opt-in/out toggle in Preferences)
- **Per-Category Preferences** (Preferences → Notifications): Fine-grained control over which notification categories appear in-app and trigger email delivery:
  - *Account Syncs*: sync failures, re-auth prompts, stale account warnings
  - *Account Activity*: new connections, large transactions, duplicate detection
  - *Budget Alerts*: threshold breach notifications
  - *Milestones & FIRE*: portfolio highs, Coast FI reached, FI achieved
  - *Household*: member changes, retirement scenario staleness

## Background Automation (Celery)

Scheduled tasks for hands-free operation:

- **Daily Budget Alerts** (Midnight): Check all budgets and create notifications
- **Weekly Recurring Detection** (Monday 2am): Auto-detect recurring transactions/subscriptions
- **Daily Cash Flow Forecast** (6:30am): Check for projected negative balances
- **Daily Data Retention** (3:30am): Purge transactions older than `DATA_RETENTION_DAYS` (disabled by default; dry-run safety)
- **Daily Holdings Price Update** (6:00pm EST): Refresh current prices for all stale holdings from Yahoo Finance
- **Daily Holdings Metadata Enrichment** (7:00pm EST): Enrich sector, industry, asset type, and expense ratios
  - Fetches `expenseRatio` from yfinance; falls back to the static `KNOWN_EXPENSE_RATIOS` table
  - Only writes to holdings where the value is currently NULL (never overwrites manual entries)
  - Invalidates `fee-analysis:*` and `portfolio:summary:*` caches after completion
- **Daily Portfolio Snapshots** (11:59pm): Capture end-of-day holdings values
  - Household-level snapshot (combined) plus per-user snapshots for each active member
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

## Household Guest Access

Invite external users to view or collaborate on your household data without joining as full members:

- **Guest Roles**:
  - **Viewer**: Read-only access to household financial data — ideal for family members who want visibility
  - **Advisor**: Can view and edit household data — designed for financial advisors or accountants
- **Invite by Email**: Send invitations to any email address; recipients accept or decline from their account
- **Accept / Decline Flow**: Invited users receive a pending invitation they can accept or decline
- **Revoke Access**: Household admins can instantly revoke a guest's access at any time
- **Household Switcher**: Guests can switch between their own household and any households they have guest access to
- **Security**:
  - Guest data is fully isolated — guests cannot see other guests or access data beyond their granted role
  - Revocation is instant and severs all access immediately
  - Rate limiting on invitation endpoints to prevent abuse

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
- **Household-Wide Planning**: Aggregate all household members' accounts into a single retirement scenario
  - **Selective Multi-User Scenarios**: Pick specific household members for a joint retirement plan (not just single-user or all-users)
  - Member picker modal with "Just me", "All members", or checkbox selection for specific members
  - Multi-member badge on scenario tabs showing member count
  - Automatic staleness detection when household membership changes (members join or leave)
  - "Recalculate" action refreshes scenario with current membership
  - Per-member, selective-member, or combined-household scenarios supported
- **Scenario Archival Lifecycle**: Auto-archive selective scenarios when a participating member leaves
  - Archived scenarios shown in collapsible section with "Restore" option
  - Reactivation available when departed member returns to household
  - 30-day auto-delete for archived scenarios with zero active members (Celery beat task)
- **CSV Export**: Download projection data for external analysis

## FIRE Dashboard (Financial Independence, Retire Early)

Track your progress toward financial independence with real-time metrics:

- **FI Ratio**: How close your investable assets are to covering annual expenses indefinitely (at your chosen withdrawal rate)
- **Savings Rate**: Percentage of income you're saving, calculated from categorized transactions
- **Years to FI**: Estimated time until your investments can sustain your lifestyle, factoring in growth and savings
- **Coast FI**: Whether your current investments would grow to your FI number by retirement age — even without further contributions
- **Configurable Assumptions**: Adjust withdrawal rate and expected return with 2-decimal precision (e.g. 3.75%), retirement age (30-100)
  - Assumptions panel always visible during recalculation
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

## Financial Health Score

Composite snapshot of your overall financial wellness:

- **Four Pillars**: Savings rate, emergency fund coverage, debt-to-income ratio, retirement progress
- **Weighted Score**: Single 0-100 score with color-coded badge (red/yellow/green)
- **Trend Tracking**: Month-over-month score history so you can see improvement over time
- **Dashboard Widget**: `FinancialHealthWidget` available on the main dashboard
- **Household Support**: Per-member or combined household scoring

## Net Worth Milestones & All-Time-High Alerts

Celebrate progress and stay informed:

- **Milestone Detection**: Configurable net worth thresholds (e.g., $100k, $250k, $500k)
- **Confetti Celebration Modal**: Crossing a milestone triggers a confetti animation with a celebration modal
- **Highest Threshold Only**: When multiple milestones are crossed at once, only the highest threshold is displayed — no redundant celebrations for intermediate levels
- **Batch Dismissal**: Dismiss all pending milestone notifications at once instead of clearing them one by one
- **All-Time-High Alerts**: Automatic notification when net worth exceeds its previous peak
- **Notification Integration**: Milestones delivered through the existing notification system (in-app + optional email)
- **Household Support**: Tracks milestones for combined household and individual members

## Transaction Notes & Flagged for Review

Add context to transactions and streamline household review:

- **Free-Text Notes**: Add notes to any transaction for additional context
- **Flagged for Review**: Mark transactions for household member attention
- **Review Workflow**: Flagged transactions appear in a dedicated filter for easy triage
- **Household Collaboration**: One member flags, another reviews — visible in combined view

## Investment Fee Analyzer

Understand the true cost of your portfolio (fully integrated into the Investments Optimization tab):

- **Fee Drag Projections**: Model how expense ratios erode returns over 10/20/30-year horizons
- **Benchmark Comparison**: Compare total portfolio cost against VTI (0.03%) over 10 and 20 years
- **Fund Overlap Detection**: Identify duplicate holdings across funds to reduce redundancy
- **Low-Cost Alternatives**: Suggest lower-fee ETF/index fund replacements for high-cost holdings
- **Per-Holding Breakdown**: Sortable table showing each holding's ER, fee flag (ok / high_cost / extreme_cost), and 10-year fee drag
- **Fee Summary Panel**: `FeeAnalysisPanel` component with total weighted expense ratio and projected savings

### Expense Ratio (ER) Data Sources

Expense ratios are resolved via a priority chain so data is always available even for newly added holdings:

1. **Stored DB value** — manually entered or previously enriched; never overwritten automatically
2. **Yahoo Finance API** (`yfinance`) — `expenseRatio` / `annualReportExpenseRatio` from `Ticker.info`; free, no key required
3. **Static fallback table** (`KNOWN_EXPENSE_RATIOS`) — ~150 common ETF/fund tickers hardcoded as a compile-time safety net
4. **Asset-class estimate** — e.g. `domestic_bond: 0.10%`, used when no authoritative value exists
5. **Asset-type estimate** — e.g. `etf: 0.20%`, broadest fallback
6. **0.0%** — for individual stocks (no ER concept) or completely unknown holdings

Holdings with estimated ERs are annotated with `~est` in the UI and include a tooltip explaining the source.

### Nightly ER Enrichment (Celery Task)

The `enrich_holdings_metadata` Celery task (runs daily at 7 PM EST) automatically populates expense ratios:

- Calls `YahooFinanceProvider.get_holding_metadata()` for each unique ticker
- Writes API-sourced ER to `Holding.expense_ratio` when the column is currently `NULL`
- Falls back to the static `KNOWN_EXPENSE_RATIOS` table when the API returns no value
- **Never overwrites** an existing non-null ER (preserves manual entries)
- Invalidates `fee-analysis:*` and `portfolio:summary:*` cache patterns after enrichment

## Year-in-Review

Annual financial summary with year-over-year comparison:

- **Dedicated Page**: `YearInReviewPage` with full-year financial recap
- **Key Metrics**: Total income, total expenses, net savings, investment returns, net worth change
- **YoY Comparison**: Side-by-side comparison with the previous year (absolute and percentage change)
- **Category Breakdown**: Top spending and income categories for the year
- **Exportable**: Download summary data for records or tax prep
- **Dynamic Year Selection**: Shows all years with transaction data (fetched via API), persists selection via localStorage

## Unified Financial Calendar

Visualize upcoming financial events in one place:

- **Bills, Subscriptions & Income**: All recurring items displayed on a single calendar view
- **Category Toggles**: Show/hide bills, subscriptions, or income streams independently
- **Projected Daily Balance**: Running balance projection overlaid on the calendar
- **Upcoming Alerts**: Highlights days with large expected outflows

## Education Planning

Track and project college savings:

- **529 Contribution Tracking**: Log contributions to 529 plans with running totals
- **College Cost Projections**: Estimate future tuition using configurable inflation rates
- **Funding Gap Analysis**: Compare projected savings to estimated costs at enrollment date
- **Dedicated Page**: `EducationPlanningPage` with per-beneficiary tracking
- **Household Support**: Multiple beneficiaries across household members

## Rental Property Profit & Loss

Per-property financial tracking for real estate investors:

- **Per-Property P&L**: Income, expenses, and net operating income for each property
- **Schedule E Categories**: Expense categories aligned with IRS Schedule E (mortgage interest, repairs, depreciation, insurance, taxes, etc.)
- **Cap Rate Calculation**: Automatic capitalization rate based on NOI and property value
- **Monthly Breakdown**: Month-by-month P&L table with year-to-date totals
- **Dedicated Page**: `RentalPropertiesPage` with multi-property dashboard

## Dividend & Investment Income

Track all forms of investment income with detailed analytics:

- **Income Types**: Dividend, qualified dividend, capital gain distribution, return of capital, interest, reinvested dividend
- **DRIP Support**: Record reinvested dividends with shares acquired, reinvestment price, and automatic cost basis tracking
- **Summary Dashboard**: YTD income, trailing 12-month income, monthly average, projected annual income
- **Year-over-Year Growth**: Automatic calculation of income growth percentage vs prior year
- **Monthly Trend Chart**: Bar chart showing dividend income by month (last 12 months) in the Investments page
- **Top Payers Table**: Ranked list of highest-paying holdings with total income, payment count, and yield-on-cost
- **By-Ticker Breakdown**: Per-holding income totals with average per-share amount and latest ex-date
- **By-Month Breakdown**: Monthly aggregates with income type breakdown (dividends vs interest vs distributions)
- **Filtering**: Filter by account, ticker, income type, and date range
- **API Endpoints**: `GET /api/v1/dividend-income/summary`, `GET /api/v1/dividend-income/`, `POST /api/v1/dividend-income/`, `DELETE /api/v1/dividend-income/{id}`

## Age-Aware Tax Advisor

Proactive tax insights that adapt to the user's age and financial situation:

- **LTCG 0% Bracket Detection**: Identifies when taxable income is low enough for 0% long-term capital gains rate (single: <$47,025, married: <$94,050)
- **Social Security Taxation**: Calculates what percentage of SS benefits are taxable (0%, 50%, or 85%) based on combined income
- **IRMAA Planning**: Warns when MAGI approaches Medicare Part B/D surcharge brackets (starts at $103,000 single / $206,000 married)
- **Net Investment Income Surtax**: Flags the 3.8% NII surtax when MAGI exceeds $200,000 (single) / $250,000 (married)
- **RMD Planning**: Age 73+ reminders with calculated Required Minimum Distribution amounts from pre-tax accounts
- **Roth Conversion Window**: Identifies tax-efficient conversion opportunities (between retirement and RMD age, or low-income years)
- **Standard Deduction (65+)**: Notes the additional $1,950 (single) / $1,550 (married) deduction for seniors
- **HSA Triple Tax Advantage**: Highlights HSA benefits for those still eligible (under 65)
- **Age-Appropriate Contribution Limits**: Shows catch-up limits for 401k ($7,500 at 50+), IRA ($1,000 at 50+), and HSA ($1,000 at 55+)
- **API Endpoint**: `GET /api/v1/tax-advisor/insights`

## Enhanced Financial Trends

**Multi-Year Trends** page dynamically fetches available years from the API (`GET /income-expenses/available-years`) instead of hardcoding. Up to 3 years can be compared simultaneously. Selected years and primary year persist via localStorage across page refreshes.

Additional trend analysis endpoints for deeper financial insight:

- **Net Worth History**: Time series from daily snapshots with asset/liability breakdown, filterable by user and date range
  - `GET /api/v1/enhanced-trends/net-worth-history`
- **Investment Performance**: Per-holding gain/loss analysis with total return, top winners, and biggest losers
  - `GET /api/v1/enhanced-trends/investment-performance`
- **Spending Velocity**: Month-over-month spending change with acceleration/deceleration trend detection
  - `GET /api/v1/enhanced-trends/spending-velocity`
- **Cash Flow History**: Monthly income vs expenses time series with savings rate per month
  - `GET /api/v1/enhanced-trends/cash-flow-history`
- **Investment Income Trend**: Monthly dividend/interest income with cumulative total for charting
  - `GET /api/v1/enhanced-trends/investment-income-trend`

## Centralized Financial Constants

All tax rates, contribution limits, RMD tables, and financial thresholds in a single admin-editable file:

- **Location**: `backend/app/constants/financial.py`
- **Organized by Domain**: `TAX`, `RETIREMENT`, `SS`, `MEDICARE`, `HEALTHCARE`, `RMD`, `EDUCATION`, `FIRE`, `HEALTH`, `PORTFOLIO`, `LIFE_EVENTS`
- **Annual Review Tags**: Constants that change with tax law are marked with `# ANNUAL` comments for easy grep
- **Single Source of Truth**: All 11 backend services import from this one file — no hardcoded tax rates scattered across the codebase
- **Key Constants Include**:
  - Federal/state tax rates, LTCG brackets (0%/15%/20%), NII surtax (3.8%), standard deductions
  - 401k/IRA/HSA/SEP/SIMPLE/529 contribution limits with age-based catch-ups
  - Social Security PIA bend points, replacement rates, FRA table, taxable max ($168,600)
  - Medicare Part B/D premiums, IRMAA brackets (6 tiers)
  - RMD Uniform Lifetime Table (ages 72-120), trigger age 73, penalty rates
  - FIRE assumptions (4% rule, 25x multiplier, default return/inflation)
  - Financial health grade thresholds and retirement benchmarks
  - Portfolio preset allocations (Bogleheads, 60/40, Target 2050, Conservative, All Weather)
  - Life event dollar amounts for retirement planning presets
- **Backward Compatible**: Services that previously defined their own constants now import from `financial.py` with no API changes

## Financial Planning Tools

Three purpose-built planning tools under `GET /api/v1/financial-planning/`.
All endpoints accept an optional `user_id` query parameter so they respect
the active household view (individual member vs combined). Pages live under
**Planning** in the nav.

### Mortgage Analyzer (`/mortgage`)

- **Automatic Data Sourcing**: Balance, rate, and remaining term pulled directly from the linked mortgage account — no manual entry
- **Full Amortization Schedule**: Month-by-month principal/interest/balance breakdown
- **Refinance Comparison**: Side-by-side current vs new rate scenarios — monthly savings, lifetime interest savings, break-even month
- **Extra Payment Impact**: Shows months saved and interest avoided by adding a fixed extra principal payment each month
- **Equity Milestones**: Month and date when equity crosses 20%, 50%, 80%, and 100%
- **Household Scoping**: Filtered to the selected member when a specific user view is active
- **Tooltips**: Plain-English explanations on every stat card, form input, result metric, and amortization table column header
- **Persistent Inputs**: Refinance rate, term, closing costs, and extra payment are remembered across page refreshes via localStorage

### Social Security Optimizer (`/ss-claiming`)

- **Age 62–70 Comparison**: Monthly benefit, annual benefit, and lifetime total for every integer claiming age
- **Three Longevity Scenarios**: Pessimistic (die at 78), base (die at 85), optimistic (die at 92) — optimal age identified for each
- **Break-Even Analysis**: Months after your 62nd birthday when waiting pays off vs claiming early
- **PIA Estimation**: Automatic AIME → PIA calculation from salary + career length, or manual override from SSA statement
- **Spousal Benefit Estimate**: 50% of higher earner's PIA at FRA; shows benefit at 62, FRA, and 70
- **Per-User**: Runs on the selected member's salary/birth year — each household member can check their own optimal age
- **Career Start Age**: Free numeric input (any age 14–80) — not a fixed dropdown — to support varied work histories
- **Tooltips**: Plain-English explanations on all inputs (PIA, FRA, longevity scenarios, break-even) and result columns
- **Persistent Inputs**: Salary, birth year, career start age, PIA, and spouse PIA remembered across refreshes via localStorage
- **Age-Gating**: Hidden by default for users under 50 (derived from birthdate in profile). Users can override under **Preferences → Navigation Visibility**. When birthdate is not set, the page is shown to avoid accidentally hiding it.

### Savings Rate Tracker (`GET /api/v1/financial-planning/savings-rate`)

- **Monthly Trend**: Up to 12 months of income vs. expense breakdown with per-month savings rate
- **Trailing Averages**: Income-weighted trailing 3-month and 12-month savings rates
- **Best / Worst Month**: Identifies which calendar month had the highest and lowest savings rate
- **Household Scoping**: Optional `user_id` parameter scopes results to one member's accounts; omit for combined household view
- **Dashboard Widget**: `savings-rate` widget (span 1) shows current month rate, 12-month average, and a mini bar chart of the last 6 months with color-coded bars (green ≥20%, yellow ≥10%, red <10%)
- **Links to**: `/income-expenses` for the full cash flow view

### True Monthly Debt Cost (`GET /api/v1/financial-planning/debt-cost`)

- **Per-Account Breakdown**: Monthly interest cost for every active credit card, loan, student loan, and mortgage account
- **Totals**: Combined monthly interest, annual interest, and weighted average interest rate across all debt
- **Formula**: `|balance| × (annual_rate / 12)` per account — uses the interest rate stored on the account
- **Household Scoping**: Optional `user_id` scoping; combined view when omitted
- **Dashboard Widget**: `debt-cost` widget (span 1) shows monthly interest cost, annual total, weighted average rate, and a per-account breakdown of the top 5 highest-cost accounts. Hidden when total debt is zero.
- **Links to**: `/debt-payoff` for payoff planning

### Mortgage Rate Watch (`GET /api/v1/financial-planning/mortgage-rates`)

- **Live Market Rates**: Fetches current 30-yr and 15-yr fixed rates from the FRED public API (Federal Reserve / Freddie Mac) — no API key required, updated weekly
- **Your Rate Comparison**: Compares market rates against the interest rate on the user's linked mortgage account
- **Status Badge**: Color-coded alert — "Above market — consider refinancing" (red), "Below market — you have a great rate" (green), or "At market rate" (gray). Threshold: ±0.5 percentage points
- **Graceful Fallback**: Returns `null` rates when FRED is unreachable; widget shows "temporarily unavailable"
- **Household Scoping**: `user_id` parameter scopes the mortgage account lookup
- **Dashboard Widget**: `mortgage-rates` widget (span 1) shows 30-yr rate, 15-yr rate, your rate, and the comparison badge. Cached 1 hour (rates are weekly). Links to `/mortgage`.

### Bill Price Alerts (`GET /api/v1/recurring/price-increases`)

- **Automatic Detection**: Returns all active recurring transactions where the charge has increased >5% vs approximately 12 months ago
- **Per-Merchant Detail**: Shows previous and current average charge amounts and percentage change
- **Annual Impact**: Projects the extra annual cost from all detected price increases combined
- **Household Scoping**: Optional `user_id` parameter; combined view when omitted
- **Dashboard Widget**: `bill-price-alerts` widget (span 1) shows a count badge, total extra annual cost, and a list of affected merchants with old→new amounts. Shows a checkmark when no increases are detected. Links to `/recurring`.

### Tax Projection (`/tax-projection`)

- **Auto-Sourced Income**: YTD transactions annualised to a full-year estimate based on days elapsed
- **Multi-Component Tax**: Ordinary income brackets, self-employment tax (15.3%), LTCG stacked on top
- **SE Deduction**: 50% of SE tax automatically deducted before computing ordinary tax
- **Additional Deductions**: User-provided itemised deductions (mortgage interest, charitable) layered on top of standard deduction
- **Quarterly 1040-ES Schedule**: Four payments with IRS due dates (Apr 15, Jun 15, Sep 15, Jan 15)
- **Safe Harbour Check**: Compares projected tax against 100% of prior-year tax; flags if underpayment penalty risk exists
- **Bracket Breakdown**: Per-bracket income and tax owed shown in a table
- **Household Scoping**: `user_id=None` aggregates all members' transactions; a specific `user_id` shows only that member's income
- **Tooltips**: Plain-English explanations on filing status, each income/deduction line, effective vs marginal rate, SE tax, LTCG, safe harbour, bracket table, and quarterly payment schedule
- **Persistent Inputs**: Filing status, SE income, capital gains, additional deductions, and prior-year tax remembered across refreshes via localStorage

## Smart Insights

Proactive, no-input-required financial recommendations derived entirely from
live account data. Accessible at `GET /api/v1/smart-insights` and under
**Planning** in the nav.

- **Emergency Fund Gap**: Checks liquid savings vs 3–6 months of expenses
- **Roth Conversion Window**: Identifies low-income years where traditional → Roth conversion is tax-efficient
- **IRMAA Cliff Warning**: Flags income approaching Medicare IRMAA surcharge thresholds
- **Cash Drag**: Alerts when excess cash in investment accounts is earning sub-optimal returns
- **HSA Opportunity**: Identifies eligible users not maximising HSA contributions
- **Fund Fee Analysis**: Scans investment holdings for high-expense-ratio funds and projects 10/20-year drag vs benchmarks
- **Stock Concentration**: Warns when a single equity position exceeds a healthy portfolio percentage
- **LTCG Harvesting**: Suggests realising long-term gains in the 0% LTCG bracket when income allows
- **Priority Scoring**: Each insight has high/medium/low priority; cards are grouped by category (cash, tax, retirement, investing)
- **Household Scoping**: All checks respect the active user view

## Scalability Safeguards

- **Date Range Validation**: Shared utility caps queries to ~50 years
- **Pagination Depth Caps**: OFFSET limited to 10,000 on report templates and audit log
- **Merchant GROUP BY Limits**: All unbounded merchant aggregation queries capped to 500 results
- **Real Health Check**: `/health` verifies actual DB connectivity and returns 503 when unreachable
- **Dashboard Query Consolidation**: Account data fetched once (eliminates 4 redundant queries)
- **Forecast O(n) Optimization**: Transaction-by-date pre-grouping replaces O(n*days) scan
