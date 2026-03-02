"""
Logging configuration using structlog.

This module provides structured logging with JSON format
and sensitive data masking.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


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
        processors=shared_processors + [
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


# Initialize logging on module import with defaults
# This ensures logging works even if setup_logging is not called
try:
    setup_logging()
except Exception:
    # Silently fail if logging setup fails during import
    pass
