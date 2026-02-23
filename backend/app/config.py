"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Nest Egg"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Industry standard for security
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MASTER_ENCRYPTION_KEY: str  # Current key — used for all new writes
    # Key rotation: when rotating, move MASTER_ENCRYPTION_KEY → ENCRYPTION_KEY_V1 and set new key.
    # Old rows encrypted with V1 continue to decrypt; new writes use the new key + incremented version.
    ENCRYPTION_KEY_V1: Optional[str] = None  # Previous key — decryption only
    ENCRYPTION_CURRENT_VERSION: int = 1      # Version prefix for new writes (increment on rotation)

    # Plaid API
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"  # sandbox, development, production
    PLAID_WEBHOOK_SECRET: str = ""
    PLAID_ENABLED: bool = True

    # Teller API (100 free accounts/month in production!)
    TELLER_APP_ID: str = ""
    TELLER_API_KEY: str = ""
    TELLER_ENV: str = "sandbox"  # sandbox, production
    TELLER_WEBHOOK_SECRET: str = ""
    TELLER_ENABLED: bool = True
    TELLER_CERT_PATH: str = ""  # Path to Teller-issued mTLS certificate (.pem) - required for API calls

    # Market Data Provider (for investment prices)
    MARKET_DATA_PROVIDER: str = "yahoo_finance"  # yahoo_finance, alpha_vantage, finnhub
    ALPHA_VANTAGE_API_KEY: Optional[str] = None  # Free: 500 calls/day, 25/min
    FINNHUB_API_KEY: Optional[str] = None  # Free: 60 calls/min
    # How long before holdings prices are considered stale (login + daily task throttle)
    PRICE_REFRESH_COOLDOWN_HOURS: int = 6

    # ── Property Auto-Valuation ──────────────────────────────────────────────
    # Set one or more provider keys to enable the "Refresh Valuation" button.
    # When multiple are set, the UI lets the user choose; the first configured
    # provider is used when none is specified explicitly.

    # RentCast (rentcast.io) — RECOMMENDED
    # Free tier: 50 calls/month (permanent, no credit card required).
    # Sign up: https://app.rentcast.io/app/api-access
    RENTCAST_API_KEY: Optional[str] = None  # Header: X-Api-Key

    # ATTOM Data Solutions (attomdata.com)
    # Paid (30-day trial). Sign up: https://api.gateway.attomdata.com
    ATTOM_API_KEY: Optional[str] = None  # Header: apikey

    # Zillow via RapidAPI (NOT RECOMMENDED)
    # Zillow's official Zestimate API is deprecated for general developers (MLS partners only).
    # This uses an unofficial third-party RapidAPI wrapper that scrapes Zillow's site.
    # ⚠ Using this may violate Zillow's Terms of Service. Use at your own risk.
    # Sign up: https://rapidapi.com/apimaker/api/zillow-com1
    ZILLOW_RAPIDAPI_KEY: Optional[str] = None  # Header: X-RapidAPI-Key

    # ── Vehicle Auto-Valuation ───────────────────────────────────────────────
    # MarketCheck (marketcheck.com) — KBB-comparable used-car valuations via VIN.
    # NHTSA (nhtsa.dot.gov) is always used for free VIN decode (year/make/model).
    MARKETCHECK_API_KEY: Optional[str] = None  # Query param: api_key

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # CORS - Environment-specific origins
    # In production, this should be a specific domain like ["https://app.nestegg.com"]
    # In development, allow localhost
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Trusted hosts for production (prevents host header attacks)
    # SECURITY: Set to specific domains in production via ALLOWED_HOSTS env var
    # Example: ALLOWED_HOSTS=app.nestegg.com,api.nestegg.com
    # The validator will REJECT "*" in production
    ALLOWED_HOSTS: list[str] = ["*"]  # Dev only - validator enforces specific hosts in production

    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200

    # Background Jobs
    PLAID_SYNC_INTERVAL_HOURS: int = 6
    RULE_APPLICATION_INTERVAL_HOURS: int = 1

    # Sync Settings
    SYNC_INITIAL_DAYS: int = 90
    SYNC_INCREMENTAL_DAYS: int = 7
    SYNC_MAX_RETRIES: int = 3
    SYNC_RETRY_DELAY_SECONDS: int = 300

    # Rate Limiting
    MAX_MANUAL_SYNCS_PER_HOUR: int = 1

    # Authentication & Account Security
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 30

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # 'text' or 'json' (json for production)
    ENVIRONMENT: str = "development"  # development, staging, production

    # Email (SMTP) — all optional; emails are silently skipped when SMTP_HOST is unset.
    # Works with any SMTP provider: Gmail, AWS SES, SendGrid, Mailgun, etc.
    # Example: SMTP_HOST=smtp.gmail.com SMTP_PORT=587 SMTP_USE_TLS=true
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@nestegg.app"
    SMTP_FROM_NAME: str = "Nest Egg"
    SMTP_USE_TLS: bool = True  # Use STARTTLS (port 587). Set False for SSL on port 465.
    APP_BASE_URL: str = "http://localhost:5173"  # Used to build clickable links in emails

    # Prometheus Metrics
    METRICS_ENABLED: bool = True
    METRICS_INCLUDE_IN_SCHEMA: bool = False  # Hide from Swagger docs
    METRICS_ADMIN_PORT: int = 9090           # Separate port for /metrics endpoint
    METRICS_USERNAME: str = "admin"          # Basic auth username — override in prod
    METRICS_PASSWORD: str = "metrics_admin"  # Basic auth password — CHANGE IN PROD

    # Compliance
    TERMS_VERSION: str = "2026-02"  # Bump when Terms of Service or Privacy Policy changes

    # ── Identity Provider Chain ───────────────────────────────────────────────
    # Ordered comma-separated list of active providers.
    # 'builtin' = app's own HS256 JWT (always available as fallback).
    # First provider whose JWT issuer/alg matches the incoming token wins.
    # Example: "cognito,builtin" — try Cognito first, fall back to built-in.
    IDENTITY_PROVIDER_CHAIN: list[str] = ["builtin"]

    # --- AWS Cognito (add 'cognito' to IDENTITY_PROVIDER_CHAIN to enable) ---
    IDP_COGNITO_ISSUER: Optional[str] = None      # https://cognito-idp.{region}.amazonaws.com/{pool-id}
    IDP_COGNITO_CLIENT_ID: Optional[str] = None
    IDP_COGNITO_ADMIN_GROUP: str = "nest-egg-admins"

    # --- Keycloak (add 'keycloak' to IDENTITY_PROVIDER_CHAIN to enable) ---
    IDP_KEYCLOAK_ISSUER: Optional[str] = None     # https://keycloak.example.com/realms/{realm}
    IDP_KEYCLOAK_CLIENT_ID: Optional[str] = None
    IDP_KEYCLOAK_ADMIN_GROUP: str = "nest-egg-admins"
    IDP_KEYCLOAK_GROUPS_CLAIM: str = "groups"

    # --- Okta (add 'okta' to IDENTITY_PROVIDER_CHAIN to enable) ---
    IDP_OKTA_ISSUER: Optional[str] = None         # https://company.okta.com/oauth2/default
    IDP_OKTA_CLIENT_ID: Optional[str] = None
    IDP_OKTA_GROUPS_CLAIM: str = "groups"

    # --- Google (add 'google' to IDENTITY_PROVIDER_CHAIN to enable) ---
    IDP_GOOGLE_CLIENT_ID: Optional[str] = None    # Google OAuth2 client ID (validates aud claim)

    # Storage (CSV uploads, attachments)
    STORAGE_BACKEND: str = "local"           # "local" or "s3"
    LOCAL_UPLOAD_DIR: str = "/tmp/nestegg-uploads"
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None  # Omit to use IAM instance role
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_PREFIX: str = "csv-uploads/"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_string_list(cls, v):
        """Allow comma-separated strings in env vars (e.g. 'http://a.com,http://b.com')."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY is not using insecure defaults in production."""
        insecure_defaults = [
            "dev-secret-key-change-in-production",
            "dev-secret-key-change-in-production-generate-with-openssl",
            "your-secret-key-here",
            "change-me",
            "secret",
        ]

        # Get ENVIRONMENT from environment variable directly (before Settings is fully initialized)
        import os

        environment = os.getenv("ENVIRONMENT", "development")

        if environment == "production" and (v in insecure_defaults or len(v) < 32):
            raise ValueError(
                "Insecure SECRET_KEY detected in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )

        return v

    @field_validator("ALLOWED_HOSTS")
    @classmethod
    def validate_allowed_hosts(cls, v: list[str]) -> list[str]:
        """Validate ALLOWED_HOSTS is configured for production."""
        import os

        environment = os.getenv("ENVIRONMENT", "development")

        if environment == "production" and "*" in v:
            raise ValueError(
                "ALLOWED_HOSTS=['*'] is insecure in production! "
                "Set specific domains like ['app.nestegg.com', 'api.nestegg.com']"
            )

        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
