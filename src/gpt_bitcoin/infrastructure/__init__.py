"""
Infrastructure layer for the trading system.

This package contains cross-cutting concerns:
- exceptions: Custom exception hierarchy
- logging: Structured logging with structlog
- external: External API clients (GLM, Upbit)
- resilience: Retry and circuit breaker patterns
"""

from gpt_bitcoin.infrastructure.exceptions import (
    AnalysisError,
    CircuitBreakerOpenError,
    ConfigurationError,
    DataFetchError,
    DecisionError,
    ExecutionError,
    GLMAPIError,
    InsufficientBalanceError,
    RateLimitError,
    SerpApiError,
    TradingError,
    UpbitAPIError,
)

__all__ = [
    # Exceptions
    "TradingError",
    "UpbitAPIError",
    "GLMAPIError",
    "SerpApiError",
    "ConfigurationError",
    "DataFetchError",
    "AnalysisError",
    "DecisionError",
    "ExecutionError",
    "InsufficientBalanceError",
    "RateLimitError",
    "CircuitBreakerOpenError",
]
