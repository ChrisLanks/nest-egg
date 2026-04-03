# Configuration

Complete environment variable reference for Nest Egg. All variables live in `backend/.env` (for local dev) or `.env.docker` (for production Docker).

Variables marked **[required]** have no default and the app will not start without them. Everything else is optional with the defaults shown.

## Application

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `staging`, or `production`. Controls lockout bypass, security middleware, and docs visibility. |
| `DEBUG` | `false` | Enables Swagger UI at `/docs`. Always `false` in production. |
| `APP_NAME` | `Nest Egg` | Name returned in API responses. |
| `APP_VERSION` | `1.0.0` | Version string returned in API responses. |

## Database & Cache

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — **[required]** | PostgreSQL async URL, e.g. `postgresql+asyncpg://user:pass@localhost:5432/nestegg` |
| `DB_ECHO` | `false` | Log all SQL statements (very verbose — dev only). |
| `DB_POOL_SIZE` | `20` | SQLAlchemy connection pool size. |
| `DB_MAX_OVERFLOW` | `10` | Extra connections allowed above pool size. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL (rate limiting, Celery broker). |

## Security & Encryption

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
| `ENFORCE_JTI_REDIS_CHECK` | auto (`true` in prod) | When `true`, each token refresh and API call verifies the JWT ID (JTI) against Redis. Provides O(1) session revocation — revoking one token or all tokens for a user takes effect immediately. Auto-enabled in `production`/`staging`; disabled in `development`/`test` so Redis is not required locally. |
| `ALLOWED_HOSTS` | `["*"]` | Trusted host list (TrustedHostMiddleware). Must be specific domains in production. |
| `CORS_ORIGINS` | `["http://localhost:3000", "http://localhost:5173"]` | Allowed CORS origins. Set to your frontend domain in production. |
| `TERMS_VERSION` | `2026-02` | Current Terms of Service version. Bump when ToS/Privacy Policy changes — users are re-prompted. |

## Banking: Teller (optional)

Teller provides 100 free linked accounts per month in production. Set `TELLER_ENABLED=false` to disable.

| Variable | Default | Description |
|---|---|---|
| `TELLER_ENABLED` | `true` | Enable/disable Teller integration entirely. |
| `TELLER_APP_ID` | `""` | Your Teller application ID from teller.io. |
| `TELLER_API_KEY` | `""` | Teller API key. |
| `TELLER_ENV` | `sandbox` | `sandbox` or `production`. |
| `TELLER_WEBHOOK_SECRET` | `""` | Secret for verifying Teller webhook signatures. |
| `TELLER_CERT_PATH` | `""` | Path to Teller-issued mTLS certificate (`.pem`). Required for all API calls in production. |

## Banking: Plaid (optional)

Plaid supports 11,000+ institutions. Set `PLAID_ENABLED=false` to disable.

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

## Banking: MX (optional — enterprise)

MX provides 16,000+ institution coverage across US and Canada. Requires a sales contract for production access. Disabled by default.

| Variable | Default | Description |
|---|---|---|
| `MX_ENABLED` | `false` | Enable/disable MX integration. Must be explicitly enabled. |
| `MX_CLIENT_ID` | `""` | MX Platform API client ID. |
| `MX_API_KEY` | `""` | MX Platform API key. |
| `MX_ENV` | `sandbox` | `sandbox` or `production`. Sandbox: `int-api.mx.com`, Production: `api.mx.com`. |

## Investment Price Data (optional)

| Variable | Default | Description |
|---|---|---|
| `MARKET_DATA_PROVIDER` | `yahoo_finance` | Default price provider. Options: `yahoo_finance`, `alpha_vantage`, `finnhub`. |
| `ALPHA_VANTAGE_API_KEY` | — | Alpha Vantage key. Free tier: 500 calls/day, 25/min. [Sign up](https://www.alphavantage.co/support/#api-key) |
| `FINNHUB_API_KEY` | — | Finnhub key. Free tier: 60 calls/min. [Sign up](https://finnhub.io/register) |
| `PRICE_REFRESH_COOLDOWN_HOURS` | `6` | Minimum hours between automatic holding price refreshes. |

**Market data caching** — All providers are wrapped by a transparent Redis cache (`CachedMarketDataProvider`). Identical tickers are shared across all users, so a single cache entry serves every household that holds the same symbol. Current TTLs (hardcoded, configurable in a future release):

| Data | Cache key pattern | TTL |
|------|-------------------|-----|
| Quote (price) | `quote:{SYMBOL}` | 5 min |
| Holding metadata (sector, ER) | `metadata:{SYMBOL}` | 24 h |
| Historical prices | `historical:{SYMBOL}:{interval}:{start}:{end}` | 7 days |

## Property Auto-Valuation (optional)

At least one key must be set to enable the "Refresh Valuation" button on property accounts.

| Variable | Default | Description |
|---|---|---|
| `RENTCAST_API_KEY` | — | RentCast API key. Free tier: 50 calls/month, no credit card. **Recommended.** [Sign up](https://app.rentcast.io/app/api-access) |
| `ATTOM_API_KEY` | — | ATTOM Data Solutions key. Paid, 30-day trial. |
| `ZILLOW_RAPIDAPI_KEY` | — | Unofficial Zillow wrapper via RapidAPI. May violate Zillow ToS. |

## Vehicle Auto-Valuation (optional)

| Variable | Default | Description |
|---|---|---|
| `MARKETCHECK_API_KEY` | — | MarketCheck key for KBB-comparable used-car valuations by VIN. NHTSA VIN decode is always free and requires no key. |

## Background Jobs (Celery)

| Variable | Default | Description |
|---|---|---|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery task broker URL. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery result store URL. |
| `RULE_APPLICATION_INTERVAL_HOURS` | `1` | How often Celery re-applies categorization rules to new transactions. |

## Data Retention (optional)

| Variable | Default | Description |
|---|---|---|
| `DATA_RETENTION_DAYS` | — (indefinite) | Delete transactions, snapshots, and notifications older than this many days. Leave unset or set to `-1` to keep all data forever. Set `DATA_RETENTION_DRY_RUN=false` to enable real purges. |
| `DATA_RETENTION_DRY_RUN` | `true` | When `true`, logs what would be deleted without actually deleting. Set to `false` to enable real purges. |
| `AUDIT_LOG_RETENTION_DAYS` | — (indefinite) | Delete audit log entries older than this many days. Independent of `DATA_RETENTION_DAYS` — compliance policies often require longer audit log retention (e.g., 7 years). Leave unset to keep audit logs forever. |

## Email / SMTP (optional)

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

## Observability & Monitoring

| Variable | Default | Description |
|---|---|---|
| `SENTRY_DSN` | — | Sentry DSN for error tracking. Leave unset to disable Sentry. |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `LOG_FORMAT` | `text` | Log format: `text` (dev) or `json` (production, for log aggregators). |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics endpoint. |
| `METRICS_ADMIN_PORT` | `9090` | Port for the Prometheus `/metrics` admin server (separate from the main API). |
| `METRICS_USERNAME` | `admin` | Basic auth username for the metrics endpoint. |
| `METRICS_PASSWORD` | `metrics_admin` | Basic auth password for the metrics endpoint. **Change in production.** |

## Identity Provider Chain (optional)

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

## File Storage (optional)

| Variable | Default | Description |
|---|---|---|
| `STORAGE_BACKEND` | `local` | `local` (disk) or `s3` (AWS S3). |
| `LOCAL_UPLOAD_DIR` | `/tmp/nestegg-uploads` | Local directory for CSV uploads and attachments. Override in production. |
| `AWS_S3_BUCKET` | — | S3 bucket name (required when `STORAGE_BACKEND=s3`). |
| `AWS_REGION` | `us-east-1` | AWS region. |
| `AWS_ACCESS_KEY_ID` | — | AWS credentials. Omit to use IAM instance role. |
| `AWS_SECRET_ACCESS_KEY` | — | AWS credentials. Omit to use IAM instance role. |
| `AWS_S3_PREFIX` | `csv-uploads/` | Key prefix for S3 uploads. |

## Pagination

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_PAGE_SIZE` | `50` | Default number of items per page in list endpoints. |
| `MAX_PAGE_SIZE` | `200` | Maximum items per page allowed by list endpoints. |

## Frontend (.env)

```env
VITE_API_URL=http://localhost:8000   # Backend URL (dev only — prod uses relative /api path)
VITE_APP_NAME=Nest Egg               # App name shown in browser tab
```

## Banking Provider Comparison

All banking providers are **optional** and can be **enabled simultaneously**. The deduplication layer ensures accounts from multiple providers are never double-counted.

| Feature | Plaid | Teller | MX | Manual / CSV |
|---------|-------|--------|-----|--------------|
| **Institution Coverage** | 11,000+ (US + int'l) | 5,000+ (US only) | 16,000+ (US & Canada) | Any |
| **Cost** | Paid after free tier | 100 free accounts/month | Enterprise (sales contract) | Free |
| **Transaction Categorization** | 350+ categories | Smart categorization | Categorized | Manual |
| **Investment Accounts** | Holdings sync | Manual tracking | Manual tracking | Manual |
| **Credit Cards** | Yes | Yes | Yes | Yes |
| **Auto Balance Updates** | Yes | Yes | Yes | Manual |
| **Credentials Encrypted** | AES-256 at rest | AES-256 at rest | No stored token | N/A |

When multiple providers are enabled, users see a provider picker in the "Connect Account" flow. Existing data from any provider is always preserved — switching or adding providers is purely additive.

See also: [Teller API Details](TELLER_API.md)
