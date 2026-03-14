"""
Rate Limiting infrastructure module.

This module provides:
- TokenBucket: Token bucket algorithm for rate limiting
- RateLimiter: Multi-bucket rate limiter
- ProtectedAPIClient: Wrapper combining rate limiting, circuit breaker, and retry
- CircuitBreaker: Circuit breaker pattern for failure protection (from resilience)
- Retry decorators: Exponential backoff retry logic (from resilience)

@MX:NOTE: Rate limiting - protects external API calls from overwhelming servers
"""

from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
    ProtectedAPIClient,
    ProtectedClientStats,
)
from gpt_bitcoin.infrastructure.rate_limiting.rate_limiter import RateLimiter
from gpt_bitcoin.infrastructure.rate_limiting.token_bucket import TokenBucket

# Re-export from resilience module to maintain backward compatibility
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
    "ProtectedAPIClient",
    "ProtectedClientStats",
    "RateLimiter",
    "RetryConfig",
    "TokenBucket",
    "async_retry",
    "sync_retry",
]
