"""
Resilience patterns for external API calls.

This module provides retry and circuit breaker patterns to improve
system reliability when dealing with external services.

Components:
- retry: Tenacity-based retry decorators
- circuit_breaker: Circuit breaker pattern implementation
"""

from gpt_bitcoin.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)
from gpt_bitcoin.infrastructure.resilience.retry import (
    RetryConfig,
    async_retry,
    sync_retry,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitState",
    "RetryConfig",
    "async_retry",
    "sync_retry",
]
