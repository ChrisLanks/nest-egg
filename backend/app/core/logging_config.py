"""
Structured logging configuration for production monitoring.

This module sets up structured logging with JSON formatting for easy
parsing by log aggregation tools (Datadog, Loggly, ELK stack, etc.).

Usage:
    from app.core.logging_config import setup_logging, get_logger

    # In main.py or app startup
    setup_logging()

    # In your code
    logger = get_logger(__name__)
    logger.info("user_login", user_id=123, email="user@example.com")
"""

import logging
import logging.config
import sys
from typing import Any

import structlog
from pythonjsonlogger import jsonlogger

from app.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up both stdlib logging and structlog for structured log output.
    In production, logs are JSON formatted for easy parsing by monitoring tools.
    In development, logs are human-readable text.
    """
    # Determine log format based on environment
    use_json = settings.LOG_FORMAT == "json" or settings.ENVIRONMENT == "production"

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )

    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)

    # Configure structlog processors
    processors = [
        # Add context
        structlog.contextvars.merge_contextvars,
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add stack info
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
        # Add call site information (file, line, function)
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ],
        ),
    ]

    # Add environment-specific processors
    if use_json:
        # JSON format for production (easy to parse)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty console output for development
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure uvicorn logging
    _configure_uvicorn_logging(use_json)

    # Silence noisy loggers in production
    if settings.ENVIRONMENT == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)


def _configure_uvicorn_logging(use_json: bool = False) -> None:
    """Configure uvicorn's access and error logs with JSON formatting."""
    if use_json:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        # Apply to uvicorn loggers
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.addHandler(handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger with context support

    Example:
        >>> from app.core.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("user_login", user_id=123, email="user@example.com")
        >>> logger.error("database_error", exc_info=True, query="SELECT * FROM users")
    """
    return structlog.get_logger(name)


# Helper functions for common log patterns
def log_request(
    logger: structlog.stdlib.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs,
) -> None:
    """Log HTTP request with structured data."""
    logger.info(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_database_query(
    logger: structlog.stdlib.BoundLogger,
    query: str,
    duration_ms: float,
    rows_affected: int = 0,
    **kwargs,
) -> None:
    """Log database query with performance metrics."""
    logger.debug(
        "database_query",
        query=query[:200],  # Truncate long queries
        duration_ms=duration_ms,
        rows_affected=rows_affected,
        **kwargs,
    )


def log_celery_task(
    logger: structlog.stdlib.BoundLogger,
    task_name: str,
    task_id: str,
    status: str,
    duration_ms: float = 0,
    **kwargs,
) -> None:
    """Log Celery task execution."""
    logger.info(
        "celery_task",
        task_name=task_name,
        task_id=task_id,
        status=status,
        duration_ms=duration_ms,
        **kwargs,
    )
