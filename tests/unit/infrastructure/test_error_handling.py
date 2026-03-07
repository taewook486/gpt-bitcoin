"""
Unit tests for error handling enhancement.

Tests cover:
- Dead Letter Queue (DLQ) for failed operations
- Alert system for critical errors
- Enhanced error context with structured logging

These tests follow TDD approach to achieve 85%+ coverage.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from gpt_bitcoin.infrastructure.error_handling import (
    DeadLetterQueue,
    FailedOperation,
    AlertSystem,
    AlertLevel,
    ErrorContext,
    ErrorHandler,
)


class TestFailedOperation:
    """Test FailedOperation model."""

    def test_failed_operation_creation(self):
        """FailedOperation should store operation details."""
        operation = FailedOperation(
            operation_type="trading",
            error_message="API connection failed",
            timestamp=datetime.now(),
            payload={"order_id": "123"},
        )

        assert operation.operation_type == "trading"
        assert operation.error_message == "API connection failed"
        assert operation.payload["order_id"] == "123"

    def test_failed_operation_with_retry_count(self):
        """FailedOperation should track retry count."""
        operation = FailedOperation(
            operation_type="api_call",
            error_message="Timeout",
            retry_count=3,
        )

        assert operation.retry_count == 3

    def test_failed_operation_to_dict(self):
        """FailedOperation should serialize to dict."""
        operation = FailedOperation(
            operation_type="trading",
            error_message="Failed",
            payload={"key": "value"},
        )

        result = operation.to_dict()

        assert isinstance(result, dict)
        assert "operation_type" in result
        assert "error_message" in result


class TestDeadLetterQueue:
    """Test Dead Letter Queue functionality."""

    def test_dlq_initialization(self):
        """DeadLetterQueue should initialize empty."""
        dlq = DeadLetterQueue()

        assert len(dlq) == 0

    def test_dlq_add_operation(self):
        """DeadLetterQueue should add failed operations."""
        dlq = DeadLetterQueue()
        operation = FailedOperation(
            operation_type="test",
            error_message="Test error",
        )

        dlq.add(operation)

        assert len(dlq) == 1

    def test_dlq_get_all(self):
        """DeadLetterQueue should return all operations."""
        dlq = DeadLetterQueue()
        dlq.add(FailedOperation(operation_type="test1", error_message="Error 1"))
        dlq.add(FailedOperation(operation_type="test2", error_message="Error 2"))

        operations = dlq.get_all()

        assert len(operations) == 2

    def test_dlq_get_by_type(self):
        """DeadLetterQueue should filter by operation type."""
        dlq = DeadLetterQueue()
        dlq.add(FailedOperation(operation_type="trading", error_message="Error 1"))
        dlq.add(FailedOperation(operation_type="api", error_message="Error 2"))
        dlq.add(FailedOperation(operation_type="trading", error_message="Error 3"))

        trading_ops = dlq.get_by_type("trading")

        assert len(trading_ops) == 2

    def test_dlq_remove(self):
        """DeadLetterQueue should remove specific operation."""
        dlq = DeadLetterQueue()
        operation = FailedOperation(operation_type="test", error_message="Error")
        dlq.add(operation)

        dlq.remove(operation)

        assert len(dlq) == 0

    def test_dlq_clear(self):
        """DeadLetterQueue should clear all operations."""
        dlq = DeadLetterQueue()
        dlq.add(FailedOperation(operation_type="test1", error_message="Error 1"))
        dlq.add(FailedOperation(operation_type="test2", error_message="Error 2"))

        dlq.clear()

        assert len(dlq) == 0

    def test_dlq_max_size(self):
        """DeadLetterQueue should respect max size limit."""
        dlq = DeadLetterQueue(max_size=3)

        for i in range(5):
            dlq.add(FailedOperation(operation_type=f"test{i}", error_message=f"Error {i}"))

        assert len(dlq) <= 3


class TestAlertLevel:
    """Test AlertLevel enum."""

    def test_alert_levels_exist(self):
        """AlertLevel should have standard levels."""
        from enum import Enum

        assert issubclass(AlertLevel, Enum)
        assert hasattr(AlertLevel, "INFO")
        assert hasattr(AlertLevel, "WARNING")
        assert hasattr(AlertLevel, "ERROR")
        assert hasattr(AlertLevel, "CRITICAL")


class TestAlertSystem:
    """Test Alert System functionality."""

    def test_alert_system_initialization(self):
        """AlertSystem should initialize with handlers."""
        alert_system = AlertSystem()

        assert alert_system is not None

    def test_alert_system_send_info(self):
        """AlertSystem should send info level alerts."""
        alert_system = AlertSystem()

        # Should not raise
        alert_system.send("Test info message", level=AlertLevel.INFO)

    def test_alert_system_send_error(self):
        """AlertSystem should send error level alerts."""
        alert_system = AlertSystem()

        alert_system.send("Test error message", level=AlertLevel.ERROR)

    def test_alert_system_send_critical(self):
        """AlertSystem should send critical level alerts."""
        alert_system = AlertSystem()

        alert_system.send("Test critical message", level=AlertLevel.CRITICAL)

    def test_alert_system_with_context(self):
        """AlertSystem should include context in alerts."""
        alert_system = AlertSystem()

        alert_system.send(
            "Test message",
            level=AlertLevel.WARNING,
            context={"operation": "trading", "coin": "BTC"},
        )

    def test_alert_system_add_handler(self):
        """AlertSystem should accept custom handlers."""
        alert_system = AlertSystem()
        handler = MagicMock()

        alert_system.add_handler(handler)

        assert handler in alert_system.handlers

    @pytest.mark.asyncio
    async def test_alert_system_async_send(self):
        """AlertSystem should support async sending."""
        alert_system = AlertSystem()

        await alert_system.send_async("Async message", level=AlertLevel.INFO)


class TestErrorContext:
    """Test ErrorContext model."""

    def test_error_context_creation(self):
        """ErrorContext should store error details."""
        context = ErrorContext(
            error_type="ConnectionError",
            message="Failed to connect to API",
            timestamp=datetime.now(),
        )

        assert context.error_type == "ConnectionError"
        assert context.message == "Failed to connect to API"

    def test_error_context_with_stack_trace(self):
        """ErrorContext should store stack trace."""
        context = ErrorContext(
            error_type="ValueError",
            message="Invalid value",
            stack_trace="Traceback...",
        )

        assert context.stack_trace == "Traceback..."

    def test_error_context_with_additional_info(self):
        """ErrorContext should store additional info."""
        context = ErrorContext(
            error_type="APIError",
            message="Rate limit exceeded",
            additional_info={
                "retry_after": 60,
                "endpoint": "/orders",
            },
        )

        assert context.additional_info["retry_after"] == 60

    def test_error_context_to_dict(self):
        """ErrorContext should serialize to dict."""
        context = ErrorContext(
            error_type="TestError",
            message="Test message",
        )

        result = context.to_dict()

        assert isinstance(result, dict)
        assert "error_type" in result
        assert "message" in result


class TestErrorHandler:
    """Test ErrorHandler functionality."""

    def test_error_handler_initialization(self):
        """ErrorHandler should initialize with DLQ and AlertSystem."""
        handler = ErrorHandler()

        assert handler.dlq is not None
        assert handler.alert_system is not None

    def test_error_handler_handle_exception(self):
        """ErrorHandler should handle exceptions."""
        handler = ErrorHandler()
        exception = ValueError("Test error")

        handler.handle(exception, operation_type="test")

        assert len(handler.dlq) == 1

    def test_error_handler_handle_with_alert(self):
        """ErrorHandler should send alert for critical errors."""
        mock_alert_system = MagicMock(spec=AlertSystem)
        handler = ErrorHandler(alert_system=mock_alert_system)

        handler.handle(
            ValueError("Critical error"),
            operation_type="trading",
            alert_level=AlertLevel.CRITICAL,
        )

        mock_alert_system.send.assert_called()

    def test_error_handler_with_context(self):
        """ErrorHandler should preserve error context."""
        handler = ErrorHandler()

        handler.handle(
            ValueError("Test error"),
            operation_type="api_call",
            context={"endpoint": "/orders", "method": "POST"},
        )

        operations = handler.dlq.get_all()
        assert operations[0].context["endpoint"] == "/orders"

    def test_error_handler_get_failed_operations(self):
        """ErrorHandler should return failed operations."""
        handler = ErrorHandler()
        handler.handle(ValueError("Error 1"), operation_type="test1")
        handler.handle(ValueError("Error 2"), operation_type="test2")

        failed = handler.get_failed_operations()

        assert len(failed) == 2

    def test_error_handler_retry_failed_operation(self):
        """ErrorHandler should support retrying failed operations."""
        handler = ErrorHandler()
        handler.handle(ValueError("Error"), operation_type="test")

        operation = handler.dlq.get_all()[0]
        handler.retry(operation)

        # After retry, operation should have incremented retry count
        assert operation.retry_count >= 1
