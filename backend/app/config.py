"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Optional

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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MASTER_ENCRYPTION_KEY: str

    # Plaid API
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"  # sandbox, development, production
    PLAID_WEBHOOK_SECRET: str = ""

    # Financial Data APIs (free tiers for market cap/metadata)
    ALPHA_VANTAGE_API_KEY: Optional[str] = None  # Free: 25 calls/day, 5/min
    FINNHUB_API_KEY: Optional[str] = None  # Free: 60 calls/min

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000

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

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
