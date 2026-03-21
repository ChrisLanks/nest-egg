"""Database configuration and session management."""

import logging
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base

from app.config import settings

_logger = logging.getLogger(__name__)

# Create async engine with security and performance settings
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,  # Connection pool size (default: 20)
    max_overflow=settings.DB_MAX_OVERFLOW,  # Extra connections allowed (default: 10)
    pool_pre_ping=True,  # Verify connections before use (prevents stale connections)
    pool_recycle=3600,  # Recycle connections after 1 hour (prevents timeout)
    connect_args={
        "server_settings": {
            "application_name": "nest_egg_api",  # Identify app in database logs
            "statement_timeout": str(
                settings.DB_STATEMENT_TIMEOUT_MS
            ),  # Configurable query timeout
        },
    },
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def _guard_guest_org_flush(session, flush_context, instances):
    """
    SQLAlchemy before_flush event listener that prevents accidental writes
    of a guest-overridden organization_id back to the database.
    """
    from sqlalchemy import inspect as sa_inspect

    from app.models.user import User

    for obj in session.dirty:
        if isinstance(obj, User) and getattr(obj, "_is_guest", False):
            history = sa_inspect(obj).attrs.organization_id.history
            if history.has_changes():
                _logger.critical(
                    "BLOCKED: attempt to flush guest-overridden org_id for user %s",
                    obj.id,
                )
                raise RuntimeError("Cannot flush guest-overridden organization_id to database")


# Register the flush guard on the sync Session class so it fires on every flush.
# AsyncSession delegates flush to its inner sync Session, so this covers async too.
event.listen(Session, "before_flush", _guard_guest_org_flush)


async def init_db() -> None:
    """Initialize database tables (use Alembic migrations in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
