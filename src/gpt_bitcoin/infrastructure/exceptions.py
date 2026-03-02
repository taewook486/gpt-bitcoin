"""
Custom exception hierarchy for the trading system.

This module defines specific exceptions for better error handling
and enables proper error context in log messages.
"""

from typing import Any, Optional


class TradingError(Exception):
    """Base exception for trading operations."""

    def __init__(self, message: str, context: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}


class UpbitAPIError(TradingError):
    """Exception for Upbit API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, {"status_code": status_code, "response": response_data})
        self.status_code = status_code
        self.response_data = response_data


class GLMAPIError(TradingError):
    """Exception for GLM API errors."""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message, {"model": model, "status_code": status_code})
        self.model = model
        self.status_code = status_code


class SerpApiError(TradingError):
    """Exception for SerpApi errors."""

    def __init__(self, message: str, query: Optional[str] = None):
        super().__init__(message, {"query": query})
        self.query = query


class ConfigurationError(TradingError):
    """Exception for configuration errors."""

    def __init__(self, message: str, setting_name: Optional[str] = None):
        super().__init__(message, {"setting_name": setting_name})
        self.setting_name = setting_name


class DataFetchError(TradingError):
    """Exception for data fetching errors."""

    def __init__(self, message: str, source: Optional[str] = None):
        super().__init__(message, {"source": source})
        self.source = source


class AnalysisError(TradingError):
    """Exception for analysis errors."""

    def __init__(self, message: str, data_type: Optional[str] = None):
        super().__init__(message, {"data_type": data_type})
        self.data_type = data_type


class DecisionError(TradingError):
    """Exception for decision making errors."""

    def __init__(self, message: str, decision: Optional[str] = None):
        super().__init__(message, {"decision": decision})
        self.decision = decision


class ExecutionError(TradingError):
    """Exception for trade execution errors."""

    def __init__(
        self,
        message: str,
        order_type: Optional[str] = None,
        ticker: Optional[str] = None,
    ):
        super().__init__(message, {"order_type": order_type, "ticker": ticker})
        self.order_type = order_type
        self.ticker = ticker


class InsufficientBalanceError(TradingError):
    """Exception for insufficient balance."""

    def __init__(self, currency: str, available: float, required: float):
        message = f"Insufficient {currency} balance: available={available}, required={required}"
        super().__init__(
            message,
            {"currency": currency, "available": available, "required": required},
        )
        self.currency = currency
        self.available = available
        self.required = required


class RateLimitError(TradingError):
    """Exception for rate limiting."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, {"retry_after": retry_after})
        self.retry_after = retry_after


class CircuitBreakerOpenError(TradingError):
    """Exception when circuit breaker is open."""

    def __init__(self, service_name: str, recovery_time: Optional[float] = None):
        message = f"Circuit breaker open for {service_name}"
        super().__init__(message, {"service": service_name, "recovery_time": recovery_time})
        self.service_name = service_name
        self.recovery_time = recovery_time
