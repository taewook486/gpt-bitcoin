"""
Logging configuration using structlog.

This module provides structured logging with JSON format,
sensitive data masking, and correlation ID tracking.

@MX:NOTE: Implements SPEC-MODERNIZE-001 Section 2.2 structured logging requirements.
"""

from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

import structlog

# Context variables for correlation tracking
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "console",
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_format: Output format ("console" or "json")
    """
    # Map string to logging level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    level = level_map.get(log_level.upper(), logging.INFO)

    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        mask_sensitive_data_processor,
    ]

    if log_format == "json":
        # JSON format for production
        renderer = structlog.processors.JSONRenderer()
    else:
        # Console format for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def mask_sensitive_data_processor(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Structlog processor to mask sensitive data.

    Args:
        logger: The wrapped logger object
        method_name: The name of the wrapped method
        event_dict: The event dictionary to process

    Returns:
        Processed event dictionary with sensitive data masked
    """
    sensitive_fields = {
        "api_key",
        "access_key",
        "secret_key",
        "password",
        "token",
        "authorization",
        "credential",
    }

    for field in sensitive_fields:
        if field in event_dict:
            value = event_dict[field]
            if isinstance(value, str) and len(value) > 4:
                # Show first 4 characters, mask the rest
                event_dict[field] = value[:4] + "*" * (len(value) - 4)
            else:
                event_dict[field] = "****"

    return event_dict


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured structlog logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        A bound structlog logger instance
    """
    return structlog.get_logger(name)


def get_correlation_id() -> str | None:
    """
    Get the current correlation ID from context.

    Returns:
        The current correlation ID or None if not set
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str | None) -> None:
    """
    Set the correlation ID in the current context.

    Args:
        correlation_id: The correlation ID to set, or None to clear
    """
    _correlation_id.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    _correlation_id.set(None)


def generate_correlation_id() -> str:
    """
    Generate a new unique correlation ID.

    Returns:
        A UUID-based correlation ID string
    """
    return str(uuid.uuid4())


@contextmanager
def bind_correlation_context(
    correlation_id: str | None = None,
    **extra_context: Any,
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager to bind correlation ID and extra context to logs.

    Args:
        correlation_id: Optional correlation ID (generates one if not provided)
        **extra_context: Additional context to bind

    Yields:
        Dictionary with the bound context values

    Example:
        ```python
        with bind_correlation_context(user_id="123", request_id="abc"):
            logger.info("Processing request")  # Includes correlation_id, user_id, request_id
        ```
    """
    # Save previous correlation ID
    previous_correlation_id = get_correlation_id()

    # Set new correlation ID
    new_correlation_id = correlation_id or generate_correlation_id()
    set_correlation_id(new_correlation_id)

    # Bind context to structlog
    bound_context = {"correlation_id": new_correlation_id, **extra_context}
    bound_logger = structlog.contextvars.bind_contextvars(**bound_context)

    try:
        yield bound_context
    finally:
        # Restore previous correlation ID
        set_correlation_id(previous_correlation_id)
        # Clear bound context
        structlog.contextvars.unbind_contextvars(*bound_context.keys())


# Initialize logging on module import with defaults
# This ensures logging works even if setup_logging is not called
try:
    setup_logging()
except Exception:
    # Silently fail if logging setup fails during import
    pass
