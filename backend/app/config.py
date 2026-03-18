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
    DB_POOL_SIZE: int = 50
    DB_MAX_OVERFLOW: int = 30
    DB_STATEMENT_TIMEOUT_MS: int = 45000  # 45 second query timeout

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Industry standard for security
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MASTER_ENCRYPTION_KEY: str  # Current key — used for all new writes
    # Key rotation: when rotating, move MASTER_ENCRYPTION_KEY → ENCRYPTION_KEY_V1 and set new key.
    # Old rows encrypted with V1 continue to decrypt;
    # new writes use the new key + incremented version.
    ENCRYPTION_KEY_V1: Optional[str] = None  # Previous key — decryption only
    ENCRYPTION_CURRENT_VERSION: int = 1  # Version prefix for new writes (increment on rotation)

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
    TELLER_CERT_PATH: str = (
        ""  # Path to Teller-issued mTLS certificate (.pem) - required for API calls
    )
    TELLER_KEY_PATH: str = ""  # Path to private key (.pem) if separate from cert file

    # MX Platform API (enterprise — requires sales contract for production)
    # Sandbox: https://int-api.mx.com, Production: https://api.mx.com
    # Auth: HTTP Basic (client_id:api_key)
    MX_CLIENT_ID: str = ""
    MX_API_KEY: str = ""
    MX_ENV: str = "sandbox"  # sandbox, production
    MX_ENABLED: bool = False  # Disabled by default — requires enterprise agreement

    # Market Data Provider (for investment prices)
    MARKET_DATA_PROVIDER: str = "yahoo_finance"  # yahoo_finance, alpha_vantage, finnhub, coingecko
    ALPHA_VANTAGE_API_KEY: Optional[str] = None  # Free: 500 calls/day, 25/min
    FINNHUB_API_KEY: Optional[str] = None  # Free: 60 calls/min
    COINGECKO_API_KEY: Optional[str] = None  # Optional: 500 calls/min (free key tier)
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
    USER_RATE_LIMIT_PER_MINUTE: int = 300  # Per-user rate limit for authenticated endpoints

    # Authentication & Account Security
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 30
    # Explicit flags for security features — default based on ENVIRONMENT.
    # Override with env vars to enable in dev (testing) or disable in staging.
    ENFORCE_ACCOUNT_LOCKOUT: Optional[bool] = (
        None  # None = auto (enabled unless ENVIRONMENT=development)
    )
    ENFORCE_MFA: Optional[bool] = None  # None = auto (enabled unless ENVIRONMENT=development)

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # 'text' or 'json' (json for production)
    ENVIRONMENT: str = "development"  # development, staging, production
    # Set to true ONLY in pytest fixtures — never in .env files.
    # Guards CSRF bypass so it can't be triggered by a mis-set ENVIRONMENT var.
    SKIP_CSRF_IN_TESTS: bool = False

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
    METRICS_ADMIN_PORT: int = 9090  # Separate port for /metrics endpoint
    METRICS_USERNAME: str = "admin"  # Basic auth username — override in prod
    METRICS_PASSWORD: str = "metrics_admin"  # Basic auth password — CHANGE IN PROD
    METRICS_ALLOWED_HOSTS: list[str] = []  # IP/DNS allowlist (empty = allow all authenticated)

    # Compliance
    TERMS_VERSION: str = "2026-02"  # Bump when Terms of Service or Privacy Policy changes

    # Data Retention (enterprise compliance)
    # None = keep data indefinitely (default for self-hosted / small teams)
    DATA_RETENTION_DAYS: Optional[int] = None
    # Safety: dry-run logs what would be deleted without actually deleting.
    # Set to False only after verifying the retention window is correct.
    DATA_RETENTION_DRY_RUN: bool = True

    # ── Identity Provider Chain ───────────────────────────────────────────────
    # Ordered comma-separated list of active providers.
    # 'builtin' = app's own HS256 JWT (always available as fallback).
    # First provider whose JWT issuer/alg matches the incoming token wins.
    # Example: "cognito,builtin" — try Cognito first, fall back to built-in.
    IDENTITY_PROVIDER_CHAIN: list[str] = ["builtin"]

    # --- AWS Cognito (add 'cognito' to IDENTITY_PROVIDER_CHAIN to enable) ---
    IDP_COGNITO_ISSUER: Optional[str] = None  # https://cognito-idp.{region}.amazonaws.com/{pool-id}
    IDP_COGNITO_CLIENT_ID: Optional[str] = None
    IDP_COGNITO_ADMIN_GROUP: str = "nest-egg-admins"

    # --- Keycloak (add 'keycloak' to IDENTITY_PROVIDER_CHAIN to enable) ---
    IDP_KEYCLOAK_ISSUER: Optional[str] = None  # https://keycloak.example.com/realms/{realm}
    IDP_KEYCLOAK_CLIENT_ID: Optional[str] = None
    IDP_KEYCLOAK_ADMIN_GROUP: str = "nest-egg-admins"
    IDP_KEYCLOAK_GROUPS_CLAIM: str = "groups"

    # --- Okta (add 'okta' to IDENTITY_PROVIDER_CHAIN to enable) ---
    IDP_OKTA_ISSUER: Optional[str] = None  # https://company.okta.com/oauth2/default
    IDP_OKTA_CLIENT_ID: Optional[str] = None
    IDP_OKTA_GROUPS_CLAIM: str = "groups"

    # --- Google (add 'google' to IDENTITY_PROVIDER_CHAIN to enable) ---
    IDP_GOOGLE_CLIENT_ID: Optional[str] = None  # Google OAuth2 client ID (validates aud claim)

    # Storage (CSV uploads, attachments)
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    LOCAL_UPLOAD_DIR: str = "./uploads"  # Override via env var in production
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

    @field_validator("METRICS_PASSWORD")
    @classmethod
    def validate_metrics_password(cls, v: str) -> str:
        """Require a non-default metrics password in non-development environments."""
        import os

        environment = os.getenv("ENVIRONMENT", "development")
        if environment != "development" and v == "metrics_admin":
            raise ValueError(
                "Insecure default METRICS_PASSWORD detected. "
                "Set a strong password via the METRICS_PASSWORD environment variable."
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

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """Reject localhost CORS origins in production."""
        import os

        environment = os.getenv("ENVIRONMENT", "development")

        if environment == "production":
            localhost_origins = [o for o in v if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                raise ValueError(
                    f"CORS_ORIGINS contains localhost entries in production: {localhost_origins}. "
                    "Set to your public domain(s), e.g. ['https://app.nestegg.com']"
                )

        return v

    @field_validator("ENFORCE_ACCOUNT_LOCKOUT", "ENFORCE_MFA")
    @classmethod
    def resolve_security_flags(cls, v: Optional[bool]) -> bool:
        """Default security flags to True unless ENVIRONMENT=development."""
        if v is not None:
            return v
        import os

        return os.getenv("ENVIRONMENT", "development") != "development"

    @field_validator("PLAID_CLIENT_ID", "PLAID_SECRET")
    @classmethod
    def validate_plaid_credentials(cls, v: str, info) -> str:
        """Require Plaid credentials when PLAID_ENABLED=true in non-dev environments."""
        import os

        if os.getenv("ENVIRONMENT", "development") != "development":
            plaid_enabled = os.getenv("PLAID_ENABLED", "true").lower() not in ("false", "0")
            if plaid_enabled and not v:
                raise ValueError(
                    f"{info.field_name} is required when PLAID_ENABLED=true. "
                    "Set it in your environment or disable Plaid with PLAID_ENABLED=false."
                )
        return v

    @field_validator("TELLER_CERT_PATH")
    @classmethod
    def validate_teller_cert(cls, v: str) -> str:
        """Require and verify the mTLS certificate when TELLER_ENABLED=true."""
        import os

        # Treat comment-style placeholders (e.g. "# path/to/cert.pem") as empty
        if v.strip().startswith("#"):
            return ""

        if os.getenv("ENVIRONMENT", "development") != "development":
            teller_enabled = os.getenv("TELLER_ENABLED", "true").lower() not in ("false", "0")
            if teller_enabled and not v:
                raise ValueError(
                    "TELLER_CERT_PATH is required when TELLER_ENABLED=true. "
                    "Provide the path to your Teller-issued mTLS certificate (.pem)."
                )
        if v and not os.path.exists(v):
            raise ValueError(
                f"Teller certificate file not found: {v}. "
                "Verify the path is correct and the file is readable."
            )
        return v

    @field_validator("MX_CLIENT_ID", "MX_API_KEY")
    @classmethod
    def validate_mx_credentials(cls, v: str, info) -> str:
        """Require MX credentials when MX_ENABLED=true in non-dev environments."""
        import os

        if os.getenv("ENVIRONMENT", "development") != "development":
            mx_enabled = os.getenv("MX_ENABLED", "false").lower() in ("true", "1")
            if mx_enabled and not v:
                raise ValueError(
                    f"{info.field_name} is required when MX_ENABLED=true. "
                    "Contact MX for API credentials or disable with MX_ENABLED=false."
                )
        return v

    @field_validator("APP_BASE_URL")
    @classmethod
    def validate_app_base_url(cls, v: str) -> str:
        """Reject localhost APP_BASE_URL in production."""
        import os

        environment = os.getenv("ENVIRONMENT", "development")

        if environment == "production" and "localhost" in v:
            raise ValueError(
                "APP_BASE_URL contains 'localhost' in production! "
                "Set to your public URL, e.g. 'https://app.nestegg.com'"
            )

        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
