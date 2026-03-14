"""
Error handling enhancement module.

This module provides:
- Dead Letter Queue (DLQ) for failed operations
- Alert System for critical errors
- Error Context with structured logging

@MX:NOTE: Implements SPEC-MODERNIZE-001 Section 2.6 error handling requirements.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from gpt_bitcoin.infrastructure.logging import bind_correlation_context, get_logger


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FailedOperation(BaseModel):
    """
    Represents a failed operation stored in the Dead Letter Queue.

    @MX:NOTE: Stores all context needed for retry or analysis.
    """

    operation_type: str = Field(description="Type of operation that failed")
    error_message: str = Field(description="Error message from the failure")
    timestamp: datetime = Field(default_factory=datetime.now)
    payload: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = Field(default=0, description="Number of retry attempts")
    context: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "operation_type": self.operation_type,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "retry_count": self.retry_count,
            "context": self.context,
            "correlation_id": self.correlation_id,
        }


class ErrorContext(BaseModel):
    """
    Structured error context for enhanced error logging.

    @MX:NOTE: Provides rich context for debugging and monitoring.
    """

    error_type: str = Field(description="Type/class of the error")
    message: str = Field(description="Error message")
    timestamp: datetime = Field(default_factory=datetime.now)
    stack_trace: str | None = Field(default=None)
    additional_info: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
            "additional_info": self.additional_info,
            "correlation_id": self.correlation_id,
        }


class DeadLetterQueue:
    """
    Dead Letter Queue for storing failed operations.

    Provides in-memory storage for operations that failed processing,
    with optional size limits and filtering capabilities.

    Example:
        ```python
        dlq = DeadLetterQueue(max_size=100)
        dlq.add(FailedOperation(operation_type="trading", error_message="API failed"))

        # Get all failed trading operations
        trading_failures = dlq.get_by_type("trading")
        ```
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize Dead Letter Queue.

        Args:
            max_size: Maximum number of operations to store
        """
        self._queue: deque[FailedOperation] = deque(maxlen=max_size)
        self._max_size = max_size
        self._logger = get_logger("dlq")

    def __len__(self) -> int:
        """Return number of operations in queue."""
        return len(self._queue)

    @property
    def max_size(self) -> int:
        """Get maximum queue size."""
        return self._max_size

    def add(self, operation: FailedOperation) -> None:
        """
        Add a failed operation to the queue.

        Args:
            operation: The failed operation to add
        """
        self._queue.append(operation)
        self._logger.warning(
            "Operation added to DLQ",
            operation_type=operation.operation_type,
            error_message=operation.error_message,
            queue_size=len(self._queue),
        )

    def get_all(self) -> list[FailedOperation]:
        """Get all operations in the queue."""
        return list(self._queue)

    def get_by_type(self, operation_type: str) -> list[FailedOperation]:
        """
        Get operations filtered by type.

        Args:
            operation_type: Type to filter by

        Returns:
            List of matching operations
        """
        return [op for op in self._queue if op.operation_type == operation_type]

    def remove(self, operation: FailedOperation) -> bool:
        """
        Remove a specific operation from the queue.

        Args:
            operation: Operation to remove

        Returns:
            True if operation was found and removed
        """
        try:
            self._queue.remove(operation)
            return True
        except ValueError:
            return False

    def clear(self) -> None:
        """Clear all operations from the queue."""
        self._queue.clear()
        self._logger.info("DLQ cleared")


class AlertSystem:
    """
    Alert system for sending notifications about errors.

    Supports multiple alert levels and handlers for different
    notification channels (logging, email, slack, etc.).

    Example:
        ```python
        alert = AlertSystem()
        alert.add_handler(slack_handler)
        alert.send("Critical error occurred", level=AlertLevel.CRITICAL)
        ```
    """

    def __init__(self):
        """Initialize AlertSystem with default handlers."""
        self._handlers: list[Callable] = []
        self._logger = get_logger("alert_system")
        # Add default logging handler
        self._handlers.append(self._log_handler)

    @property
    def handlers(self) -> list[Callable]:
        """Get list of registered handlers."""
        return self._handlers

    def add_handler(self, handler: Callable) -> None:
        """
        Add a custom alert handler.

        Args:
            handler: Callable that accepts (message, level, context)
        """
        self._handlers.append(handler)

    def _log_handler(
        self,
        message: str,
        level: AlertLevel,
        context: dict[str, Any] | None,
    ) -> None:
        """Default logging handler."""
        log_method = {
            AlertLevel.INFO: self._logger.info,
            AlertLevel.WARNING: self._logger.warning,
            AlertLevel.ERROR: self._logger.error,
            AlertLevel.CRITICAL: self._logger.critical,
        }.get(level, self._logger.info)

        log_method(message, **(context or {}))

    def send(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Send an alert to all handlers.

        Args:
            message: Alert message
            level: Alert severity level
            context: Optional additional context
        """
        for handler in self._handlers:
            try:
                handler(message, level, context)
            except Exception as e:
                self._logger.error(
                    "Alert handler failed",
                    handler=str(handler),
                    error=str(e),
                )

    async def send_async(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Send an alert asynchronously.

        Args:
            message: Alert message
            level: Alert severity level
            context: Optional additional context
        """
        # Run in thread pool for async compatibility
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.send(message, level, context),
        )


class ErrorHandler:
    """
    Centralized error handling with DLQ and alert integration.

    Combines Dead Letter Queue and Alert System for comprehensive
    error handling with structured logging.

    Example:
        ```python
        handler = ErrorHandler()
        try:
            risky_operation()
        except Exception as e:
            handler.handle(
                e,
                operation_type="trading",
                alert_level=AlertLevel.ERROR,
                context={"order_id": "123"},
            )
        ```
    """

    def __init__(
        self,
        dlq: DeadLetterQueue | None = None,
        alert_system: AlertSystem | None = None,
    ):
        """
        Initialize ErrorHandler.

        Args:
            dlq: Dead Letter Queue instance (creates new if not provided)
            alert_system: Alert System instance (creates new if not provided)
        """
        self._dlq = dlq or DeadLetterQueue()
        self._alert_system = alert_system or AlertSystem()
        self._logger = get_logger("error_handler")

    @property
    def dlq(self) -> DeadLetterQueue:
        """Get the Dead Letter Queue."""
        return self._dlq

    @property
    def alert_system(self) -> AlertSystem:
        """Get the Alert System."""
        return self._alert_system

    def handle(
        self,
        exception: Exception,
        operation_type: str,
        alert_level: AlertLevel | None = None,
        context: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> FailedOperation:
        """
        Handle an exception by logging, storing in DLQ, and optionally alerting.

        Args:
            exception: The exception to handle
            operation_type: Type of operation that failed
            alert_level: If provided, send alert at this level
            context: Additional context for the error
            payload: Operation payload for retry

        Returns:
            The created FailedOperation
        """
        import traceback

        # Create error context
        error_context = ErrorContext(
            error_type=type(exception).__name__,
            message=str(exception),
            stack_trace=traceback.format_exc(),
            context=context or {},
        )

        # Log the error
        self._logger.error(
            "Error handled",
            operation_type=operation_type,
            error_type=error_context.error_type,
            message=error_context.message,
            **(context or {}),
        )

        # Create failed operation
        failed_op = FailedOperation(
            operation_type=operation_type,
            error_message=str(exception),
            payload=payload or {},
            context=context or {},
        )

        # Add to DLQ
        self._dlq.add(failed_op)

        # Send alert if level specified
        if alert_level:
            self._alert_system.send(
                f"Error in {operation_type}: {exception}",
                level=alert_level,
                context={
                    "operation_type": operation_type,
                    "error_type": error_context.error_type,
                    **(context or {}),
                },
            )

        return failed_op

    def get_failed_operations(self) -> list[FailedOperation]:
        """Get all failed operations from DLQ."""
        return self._dlq.get_all()

    def retry(self, operation: FailedOperation) -> None:
        """
        Mark an operation as retried.

        Args:
            operation: The operation being retried
        """
        operation.retry_count += 1
        self._logger.info(
            "Operation retry initiated",
            operation_type=operation.operation_type,
            retry_count=operation.retry_count,
        )


__all__ = [
    "AlertLevel",
    "AlertSystem",
    "DeadLetterQueue",
    "ErrorContext",
    "ErrorHandler",
    "FailedOperation",
]
