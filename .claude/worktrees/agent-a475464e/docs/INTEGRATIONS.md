# Third-Party Integrations

Nest Egg uses a plug-and-play provider architecture throughout the backend. Each integration category defines an abstract interface; concrete providers implement it and are selected at runtime via environment variables. You can run the app with as few as zero paid integrations (free tier everywhere) or wire up enterprise services as needed.

This document covers every integration point, explains what is required vs. optional, and shows how to add new providers.

---

## Table of Contents

1. [Bank Account Linking](#1-bank-account-linking)
2. [Market Data](#2-market-data)
3. [Asset Valuation](#3-asset-valuation)
4. [Email (SMTP)](#4-email-smtp)
5. [Identity Providers (SSO)](#5-identity-providers-sso)
6. [Infrastructure](#6-infrastructure)
7. [Adding New Providers](#adding-new-providers)
8. [Quick Start Configurations](#quick-start-configurations)

---

## 1. Bank Account Linking

**Status:** Choose 1 or more. At least one provider is needed for automatic account sync.

All bank linking providers are accessed through a single unified API (`/api/v1/bank-linking/`). The frontend never talks to provider-specific endpoints. The router in `backend/app/api/v1/bank_linking.py` dispatches to the correct service based on the `provider` field.

| Provider | Free Tier | Best For | Setup Complexity | Bank Coverage |
|----------|-----------|----------|------------------|---------------|
| **Plaid** | Sandbox free; production $0.30-$3/connection | Largest bank coverage, investments, most features | Medium | 11,000+ institutions (US, Canada, Europe) |
| **Teller** | 100 accounts/month FREE | Budget-friendly personal use, simple API | Low | 5,000+ US banks |
| **MX** | Enterprise only (requires sales contract) | Enterprise / institutional deployments | High | 16,000+ institutions (US, Canada) |

### Which should I pick?

- **Personal / small deployment:** Use **Teller**. The free tier (100 accounts/month) is more than enough, the API is straightforward, and there is no credit card required.
- **Maximum bank coverage:** Use **Plaid**. It covers the most institutions and is the only provider that currently supports investment holdings sync.
- **Enterprise / institutional:** Use **MX**. It requires a sales contract but offers the widest institution coverage and is built for large-scale deployments.
- **Multiple providers:** You can enable more than one simultaneously. The `/bank-linking/providers` endpoint tells the frontend which are available, and users choose at link time.

### Feature comparison

| Feature | Plaid | Teller | MX |
|---------|-------|--------|----|
| Account linking | Yes | Yes | Yes |
| Transaction sync | Yes | Yes | Yes |
| Investment holdings sync | Yes | Not yet | Not yet |
| Webhook support | Yes | Yes | Yes |
| Disconnect/revoke | Yes | Yes | Yes |

### Environment variables

**Plaid:**
```env
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox              # sandbox | development | production
PLAID_WEBHOOK_SECRET=          # optional, for webhook verification
PLAID_ENABLED=true
```

**Teller:**
```env
TELLER_APP_ID=your_app_id
TELLER_API_KEY=your_api_key
TELLER_ENV=sandbox             # sandbox | production
TELLER_WEBHOOK_SECRET=         # optional
TELLER_ENABLED=true
TELLER_CERT_PATH=              # path to mTLS certificate (production only)
```

**MX:**
```env
MX_CLIENT_ID=your_client_id
MX_API_KEY=your_api_key
MX_ENV=sandbox                 # sandbox | production
MX_ENABLED=false               # disabled by default; requires enterprise agreement
```

---

## 2. Market Data

**Status:** Choose 1. Required for investment price tracking.

Market data providers implement the `MarketDataProvider` abstract base class defined in `backend/app/services/market_data/base_provider.py`. The active provider is selected by the `MARKET_DATA_PROVIDER` environment variable and instantiated via `MarketDataProviderFactory` in `backend/app/services/market_data/provider_factory.py`.

| Provider | Free Tier | Rate Limits | Best For | Realtime |
|----------|-----------|-------------|----------|----------|
| **Yahoo Finance** (yfinance) | Free (unofficial scraper) | Unspecified, throttled | Development / personal use | No |
| **Finnhub** | 60 calls/min free | 60/min | Production use, reliable official API | Yes |
| **Alpha Vantage** | 25 calls/min, 500/day free | 25/min, 500/day | Light usage, historical data | No |
| **CoinGecko** | 10-30 calls/min (free key: 500/min) | Varies | Crypto-focused portfolios | No |

### Which should I pick?

- **Development / personal use:** Yahoo Finance is the default and works without any API key. However, it is an unofficial scraper library (`yfinance`) and should not be relied on for production -- it can break without notice when Yahoo changes their site.
- **Production:** Use **Finnhub**. It has the best free tier (60 calls/min), is an official API with stable contracts, and supports real-time quotes.
- **Light usage / historical focus:** **Alpha Vantage** works well if you only need a few price refreshes per day (500 calls/day free).
- **Crypto portfolios:** Add **CoinGecko** for cryptocurrency pricing. It can be used alongside another provider for equity data.

### Environment variables

```env
MARKET_DATA_PROVIDER=yahoo_finance   # yahoo_finance | finnhub | alpha_vantage | coingecko

# Only needed for the provider you select:
FINNHUB_API_KEY=your_key
ALPHA_VANTAGE_API_KEY=your_key
COINGECKO_API_KEY=your_key           # optional even for CoinGecko (increases rate limit)
```

### Provider interface

Every market data provider implements these methods:

| Method | Description |
|--------|-------------|
| `get_quote(symbol)` | Current price and metadata for a single symbol |
| `get_quotes_batch(symbols)` | Batch quotes for multiple symbols |
| `get_historical_prices(symbol, start, end, interval)` | OHLCV historical data |
| `search_symbol(query)` | Search securities by name or ticker |
| `get_holding_metadata(symbol)` | Sector, asset type, market cap classification |
| `supports_realtime()` | Whether the provider offers real-time data |
| `get_rate_limits()` | Rate limit information for the provider |

---

## 3. Asset Valuation

**Status:** Optional. When no provider is configured, accounts must be updated manually.

Valuation providers are defined in `backend/app/services/valuation_service.py`. Unlike market data, these do not use a formal abstract base class -- they are registered as functions in `_PROPERTY_PROVIDERS` and `_VEHICLE_PROVIDERS` dicts. The service tries providers in order and returns the first successful result.

### Property Valuation

| Provider | Free Tier | Best For | Notes |
|----------|-----------|----------|-------|
| **RentCast** | 50 calls/month free (permanent, no credit card) | Recommended for most users | Official API, stable |
| **ATTOM** | 30-day free trial, then paid | Enterprise / high volume | Comprehensive property data |
| **Zillow (RapidAPI)** | Varies by RapidAPI plan | NOT RECOMMENDED | Unofficial scraper; may violate Zillow ToS |

### Vehicle Valuation

| Provider | Free Tier | Best For | Notes |
|----------|-----------|----------|-------|
| **MarketCheck** | Limited free tier | VIN-based used car values | KBB-comparable valuations |
| **NHTSA VIN Decode** | Always free (no key needed) | Year/make/model lookup | No price data; used automatically for VIN decoding |

### Environment variables

```env
# Property (set one or more; first configured provider is used by default)
RENTCAST_API_KEY=your_key
ATTOM_API_KEY=your_key
ZILLOW_RAPIDAPI_KEY=your_key         # not recommended

# Vehicle
MARKETCHECK_API_KEY=your_key
```

---

## 4. Email (SMTP)

**Status:** Required for email verification and password resets. The app works without it but cannot send any emails.

Nest Egg uses standard SMTP via `aiosmtplib`. You can use any SMTP provider -- the service is defined in `backend/app/services/email_service.py`. When `SMTP_HOST` is not set, all email sends are silently skipped and the app exposes alternative UX paths (e.g., direct join links instead of email invitations).

| Provider | Cost | Notes |
|----------|------|-------|
| **Gmail SMTP** | Free (500/day limit) | Good for personal/dev; use App Passwords with 2FA |
| **AWS SES** | $0.10/1,000 emails | Production recommended; needs domain verification |
| **SendGrid** | 100/day free | Easy setup, good deliverability |
| **Mailgun** | 100/day free (first month: 5,000) | Developer-friendly API |
| **Any SMTP server** | Varies | Postfix, Mailtrap (testing), etc. |

### Environment variables

```env
SMTP_HOST=smtp.gmail.com           # or email-smtp.us-east-1.amazonaws.com for SES
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=noreply@nestegg.app
SMTP_FROM_NAME=Nest Egg
SMTP_USE_TLS=true                  # STARTTLS on port 587; set false for SSL on port 465
APP_BASE_URL=https://app.nestegg.com  # used to build clickable links in emails
```

---

## 5. Identity Providers (SSO)

**Status:** Optional. Built-in JWT auth works out of the box with no configuration.

The identity system uses a **provider chain** pattern. Providers are tried in order; the first one whose `can_handle()` method matches the incoming JWT processes it. This is defined in `backend/app/services/identity/chain.py`.

All external providers use a generic `OIDCIdentityProvider` that validates standard OIDC JWTs. Adding a new OIDC-compatible provider requires only a config entry -- no new code.

| Provider | Type | Setup | Notes |
|----------|------|-------|-------|
| **Built-in JWT** | HS256 | Default, no config needed | App-issued tokens; always available as fallback |
| **Google** | OIDC | Set `IDP_GOOGLE_CLIENT_ID` | Simple SSO; no group support |
| **AWS Cognito** | OIDC | Set `IDP_COGNITO_*` vars | Full SSO with group-based admin roles |
| **Keycloak** | OIDC | Set `IDP_KEYCLOAK_*` vars | Self-hosted SSO; configurable groups claim |
| **Okta** | OIDC | Set `IDP_OKTA_*` vars | Enterprise SSO |

### Environment variables

```env
# Chain order (comma-separated). First match wins. "builtin" is always the fallback.
IDENTITY_PROVIDER_CHAIN=builtin     # e.g., "cognito,builtin" or "google,builtin"

# Google
IDP_GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com

# AWS Cognito
IDP_COGNITO_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXXX
IDP_COGNITO_CLIENT_ID=your_client_id
IDP_COGNITO_ADMIN_GROUP=nest-egg-admins

# Keycloak
IDP_KEYCLOAK_ISSUER=https://keycloak.example.com/realms/nestegg
IDP_KEYCLOAK_CLIENT_ID=nestegg-app
IDP_KEYCLOAK_ADMIN_GROUP=nest-egg-admins
IDP_KEYCLOAK_GROUPS_CLAIM=groups

# Okta
IDP_OKTA_ISSUER=https://company.okta.com/oauth2/default
IDP_OKTA_CLIENT_ID=your_client_id
IDP_OKTA_GROUPS_CLAIM=groups
```

---

## 6. Infrastructure

### Required

| Service | Purpose | Config |
|---------|---------|--------|
| **PostgreSQL** | Primary database | `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/nestegg` |  <!-- pragma: allowlist secret -->
| **Redis** | Caching, rate limiting, Celery task queue | `REDIS_URL=redis://localhost:6379/0` |

### Optional

| Service | Purpose | Config |
|---------|---------|--------|
| **S3-compatible storage** | File uploads (CSV imports, attachments) | `STORAGE_BACKEND=s3`, `AWS_S3_BUCKET=...` |
| **Sentry** | Error tracking and performance monitoring | `SENTRY_DSN=https://...@sentry.io/...` |
| **Prometheus** | Metrics collection | `METRICS_ENABLED=true` (enabled by default) |

### Storage backend

The storage service (`backend/app/services/storage_service.py`) supports two backends selected by `STORAGE_BACKEND`:

- **`local`** (default): Writes files to `LOCAL_UPLOAD_DIR`. Suitable for dev and single-instance deployments.
- **`s3`**: Writes files to AWS S3. Supports IAM instance roles (recommended) or explicit credentials.

```env
# Local (default)
STORAGE_BACKEND=local
LOCAL_UPLOAD_DIR=/tmp/nestegg-uploads

# S3 (production)
STORAGE_BACKEND=s3
AWS_S3_BUCKET=my-nestegg-uploads
AWS_REGION=us-east-1
AWS_S3_PREFIX=csv-uploads/
# Leave these unset to use IAM instance role (recommended):
# AWS_ACCESS_KEY_ID=AKIA...
# AWS_SECRET_ACCESS_KEY=...
```

---

## Adding New Providers

The codebase is designed so that new providers can be added without modifying existing application logic. Each integration category has a specific extension point.

### Bank Account Linking

1. **Create a service class** following the pattern in `backend/app/services/teller_service.py` or `backend/app/services/mx_service.py`. Your service needs methods for:
   - Creating enrollments/connections
   - Syncing accounts
   - Syncing transactions
   - Revoking access

2. **Add an `AccountSource` enum value** in `backend/app/models/account.py`.

3. **Register in the bank linking router** at `backend/app/api/v1/bank_linking.py`:
   - Add your provider to the `Provider` literal type
   - Add cases in `create_link_token()`, `exchange_token()`, `sync_transactions()`, `sync_holdings()`, and `disconnect_account()`
   - Add the provider info in `list_providers()`

4. **Add a config flag** (e.g., `NEWPROVIDER_ENABLED`) in `backend/app/config.py`.

### Market Data

1. **Extend the `MarketDataProvider` base class** defined in `backend/app/services/market_data/base_provider.py`. Implement all abstract methods:
   - `get_quote()`, `get_quotes_batch()`, `get_historical_prices()`
   - `search_symbol()`, `supports_realtime()`, `get_rate_limits()`, `get_provider_name()`
   - Optionally override `get_holding_metadata()` for classification data

2. **Register in the factory** at `backend/app/services/market_data/provider_factory.py`:
   ```python
   elif provider_name == "your_provider":
       from .your_provider import YourProvider
       provider = YourProvider()
   ```

3. **Add config** in `backend/app/config.py` for the API key.

### Property / Vehicle Valuation

1. **Write a provider function** matching the signature `async def _get_property_value_xxx(address, zip_code) -> Optional[ValuationResult]` (or the vehicle equivalent).

2. **Register it** in the `_PROPERTY_PROVIDERS` or `_VEHICLE_PROVIDERS` dict in `backend/app/services/valuation_service.py`.

3. **Add it to the discovery function** (`get_available_property_providers()` or `get_available_vehicle_providers()`).

4. **Add the API key setting** in `backend/app/config.py` and add the key check to `_is_provider_configured()`.

### Identity Providers (OIDC)

If your provider is OIDC-compliant, no new code is needed:

1. **Add a config block** in `backend/app/config.py` for the issuer, client ID, and any provider-specific settings.

2. **Add a case** in `build_chain()` in `backend/app/services/identity/chain.py`:
   ```python
   elif name == "your_provider":
       providers.append(
           OIDCIdentityProvider(
               OIDCProviderConfig(
                   provider_name="your_provider",
                   issuer=settings.IDP_YOURPROVIDER_ISSUER,
                   client_id=settings.IDP_YOURPROVIDER_CLIENT_ID,
                   admin_group="",
                   groups_claim="groups",
               )
           )
       )
   ```

3. **Add your provider name** to `IDENTITY_PROVIDER_CHAIN` in the environment.

For non-OIDC providers, implement the `IdentityProvider` abstract class from `backend/app/services/identity/base.py` (methods: `can_handle()`, `validate_token()`).

---

## Quick Start Configurations

### 1. Free / Personal

Zero cost. Uses free tiers for everything. Suitable for personal finance tracking.

```env
# Database & Infrastructure
DATABASE_URL=postgresql+asyncpg://nestegg:password@localhost:5432/nestegg  # pragma: allowlist secret
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-to-a-random-string

# Bank Linking (Teller: 100 accounts/month free)
TELLER_APP_ID=your_teller_app_id
TELLER_API_KEY=your_teller_api_key
TELLER_ENV=sandbox
TELLER_ENABLED=true
PLAID_ENABLED=false
MX_ENABLED=false

# Market Data (Yahoo Finance: free, no key needed)
MARKET_DATA_PROVIDER=yahoo_finance

# Property Valuation (RentCast: 50 calls/month free)
RENTCAST_API_KEY=your_rentcast_key

# Email (Gmail SMTP: free)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=your_email@gmail.com

# Auth (built-in JWT, no external IdP)
IDENTITY_PROVIDER_CHAIN=builtin

# Storage (local filesystem)
STORAGE_BACKEND=local
```

### 2. Production

Reliable paid/free-tier services with monitoring. Suitable for a deployed product.

```env
# Database & Infrastructure
DATABASE_URL=postgresql+asyncpg://nestegg:password@db.example.com:5432/nestegg  # pragma: allowlist secret
REDIS_URL=redis://redis.example.com:6379/0
SECRET_KEY=cryptographically-random-64-char-string
ENVIRONMENT=production

# Bank Linking (Plaid: broadest coverage)
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=production
PLAID_WEBHOOK_SECRET=your_webhook_secret
PLAID_ENABLED=true
TELLER_ENABLED=false
MX_ENABLED=false

# Market Data (Finnhub: 60 calls/min free, stable API)
MARKET_DATA_PROVIDER=finnhub
FINNHUB_API_KEY=your_finnhub_key

# Property Valuation
RENTCAST_API_KEY=your_rentcast_key

# Email (AWS SES)
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your_ses_smtp_username
SMTP_PASSWORD=your_ses_smtp_password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@yourdomain.com
APP_BASE_URL=https://app.yourdomain.com

# Monitoring
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
LOG_FORMAT=json

# Auth (built-in JWT)
IDENTITY_PROVIDER_CHAIN=builtin

# Storage (S3 with IAM role)
STORAGE_BACKEND=s3
AWS_S3_BUCKET=nestegg-uploads-prod
AWS_REGION=us-east-1
```

### 3. Enterprise

Full-featured deployment with SSO, multiple bank providers, and cloud storage.

```env
# Database & Infrastructure
DATABASE_URL=postgresql+asyncpg://nestegg:password@rds.example.com:5432/nestegg  # pragma: allowlist secret
REDIS_URL=redis://elasticache.example.com:6379/0
SECRET_KEY=cryptographically-random-64-char-string
ENVIRONMENT=production

# Bank Linking (Plaid + MX for maximum coverage)
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=production
PLAID_WEBHOOK_SECRET=your_webhook_secret
PLAID_ENABLED=true
MX_CLIENT_ID=your_mx_client_id
MX_API_KEY=your_mx_api_key
MX_ENV=production
MX_ENABLED=true
TELLER_ENABLED=false

# Market Data (Finnhub: reliable, real-time)
MARKET_DATA_PROVIDER=finnhub
FINNHUB_API_KEY=your_finnhub_key

# Property & Vehicle Valuation
RENTCAST_API_KEY=your_rentcast_key
ATTOM_API_KEY=your_attom_key
MARKETCHECK_API_KEY=your_marketcheck_key

# Email (AWS SES)
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your_ses_smtp_username
SMTP_PASSWORD=your_ses_smtp_password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@enterprise.com
APP_BASE_URL=https://finance.enterprise.com

# Auth (Cognito SSO + built-in fallback)
IDENTITY_PROVIDER_CHAIN=cognito,builtin
IDP_COGNITO_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXXX
IDP_COGNITO_CLIENT_ID=your_cognito_client_id
IDP_COGNITO_ADMIN_GROUP=nest-egg-admins

# Monitoring
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
LOG_FORMAT=json
METRICS_ENABLED=true

# Storage (S3 with IAM role)
STORAGE_BACKEND=s3
AWS_S3_BUCKET=nestegg-uploads-enterprise
AWS_REGION=us-east-1
AWS_S3_PREFIX=uploads/

# Data Retention (compliance)
DATA_RETENTION_DAYS=2555
DATA_RETENTION_DRY_RUN=false
```

---

## Architecture Summary

```
Request
  |
  v
bank_linking.py ──> PlaidService / TellerService / MxService
                    (dispatched by Provider literal type)

MarketDataProviderFactory.get_provider()
  |
  v
yahoo_finance_provider.py / finnhub_provider.py / alpha_vantage_provider.py / coingecko_provider.py
  (all extend MarketDataProvider ABC)

IdentityProviderChain.authenticate()
  |
  v
BuiltinIdentityProvider / OIDCIdentityProvider(cognito|keycloak|okta|google)
  (all extend IdentityProvider ABC)

valuation_service.get_property_value() / get_vehicle_value()
  |
  v
_PROPERTY_PROVIDERS dict: rentcast / attom / zillow
_VEHICLE_PROVIDERS dict: marketcheck

get_storage_service()
  |
  v
LocalStorageService / S3StorageService
  (both satisfy StorageService Protocol)
```

Every integration follows the same principle: **define an interface, implement providers behind it, select the active provider via environment variable.** Swapping or adding providers never requires changes to the application logic that consumes them.
