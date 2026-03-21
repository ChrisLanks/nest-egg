"""Utilities for Celery async tasks.

Celery fork-pool workers run each task via ``asyncio.run()``, which creates
a new event loop every invocation.  The module-level SQLAlchemy async engine
keeps a connection pool whose connections are bound to whichever loop was
active at import time.  On the second (or retry) call the original loop is
closed, causing ``RuntimeError: Event loop is closed`` or
``Future attached to a different loop``.

Solution: build a throwaway engine with ``NullPool`` inside each task so
every ``asyncio.run()`` gets its own short-lived connections.
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings


@asynccontextmanager
async def get_celery_session():
    """Yield an ``AsyncSession`` safe for use inside ``asyncio.run()``.

    Creates a disposable engine with ``NullPool`` so there is no connection
    reuse across event loops.  The engine is disposed when the context exits.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        connect_args={
            "server_settings": {
                "application_name": "nest_egg_celery",
                "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT_MS),
            },
        },
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    try:
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()
    finally:
        await engine.dispose()
