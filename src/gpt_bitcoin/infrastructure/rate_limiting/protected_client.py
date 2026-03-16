"""
Protected API Client wrapper.

Combines rate limiting, circuit breaker, and retry logic to protect
external API calls from overwhelming servers and cascading failures.

REQ-RATE-001: Apply rate limiting to all external API calls.
REQ-RATE-003: Reject or wait when rate limit reached.
REQ-RATE-004: Retry with exponential backoff on failure.
REQ-RATE-005: Circuit breaker blocks calls when open.
REQ-RATE-002: Track statistics for monitoring.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, TypeVar

from gpt_bitcoin.infrastructure.exceptions import RateLimitError
from gpt_bitcoin.infrastructure.logging import get_logger
from gpt_bitcoin.infrastructure.rate_limiting.rate_limiter import RateLimiter
from gpt_bitcoin.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)
from gpt_bitcoin.infrastructure.resilience.retry import RetryConfig, async_retry

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class ProtectedClientStats:
    """Statistics for protected API client."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rate_limited_calls: int = 0
    circuit_blocked_calls: int = 0
    last_call_time: float | None = None


class ProtectedAPIClient:
    """
    API client wrapper with rate limiting, circuit breaker, and retry.

    This class combines three protection mechanisms:
    1. Rate Limiting: Token bucket algorithm to prevent API overload
    2. Circuit Breaker: Blocks calls to failing services
    3. Retry: Exponential backoff for temporary failures

    Flow:
        1. Check circuit breaker state
        2. Acquire rate limit permission
        3. Execute through circuit breaker
        4. Retry on failure (if configured)

    @MX:ANCHOR: ProtectedAPIClient.call
        fan_in: 2+ (GLMClient, UpbitClient, future API clients)
        @MX:REASON: Centralizes all API call protection mechanisms.
    """

    def __init__(
        self,
        client: Any,
        rate_limiter: RateLimiter,
        circuit_breaker: CircuitBreaker,
        retry_config: RetryConfig,
        rate_limit_key: str | None = None,
    ):
        """
        Initialize protected API client.

        Args:
            client: Original API client to wrap
            rate_limiter: Rate limiter instance
            circuit_breaker: Circuit breaker instance
            retry_config: Retry configuration
            rate_limit_key: Optional key for rate limiting (default: client class name)
        """
        self._client = client
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._retry_config = retry_config
        self._rate_limit_key = rate_limit_key or client.__class__.__name__
        self._stats = ProtectedClientStats()

        logger.info(
            "ProtectedAPIClient initialized",
            client=client.__class__.__name__,
            rate_limit_key=self._rate_limit_key,
        )

    async def call(
        self,
        func_name: str,
        *args: Any,
        wait: bool = False,
        timeout: float = 1.0,
        **kwargs: Any,
    ) -> Any:
        """
        Execute protected API call.

        REQ-RATE-001: Apply rate limiting.
        REQ-RATE-003: Reject or wait when rate limit reached.
        REQ-RATE-005: Circuit breaker blocks when open.
        REQ-RATE-004: Retry with exponential backoff.

        Args:
            func_name: Name of the method to call on the client
            *args: Positional arguments to pass to the method
            wait: If True, wait for rate limit token; if False, fail immediately
            timeout: Maximum time to wait for rate limit token (if wait=True)
            **kwargs: Keyword arguments to pass to the method

        Returns:
            Result of the API call

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            RateLimitError: If rate limited and wait=False
            Exception: Original exception if retries exhausted
        """
        self._stats.total_calls += 1
        self._stats.last_call_time = time.time()

        # Step 1: Check circuit breaker
        # REQ-RATE-005: Circuit breaker blocks calls when OPEN
        if self._circuit_breaker.is_open:
            self._stats.circuit_blocked_calls += 1
            logger.warning(
                "Circuit breaker open, rejecting call",
                client=self._rate_limit_key,
                func_name=func_name,
            )
            raise CircuitBreakerOpenError(
                service_name=self._rate_limit_key,
                recovery_time=self._circuit_breaker.stats.last_failure_time
                + self._circuit_breaker.recovery_timeout
                if self._circuit_breaker.stats.last_failure_time
                else None,
            )

        # Step 2: Acquire rate limit permission
        # REQ-RATE-003: Reject or wait when rate limit reached
        rate_limit_result = self._rate_limiter.check_rate_limit(self._rate_limit_key, tokens=1)

        if not rate_limit_result["allowed"]:
            self._stats.rate_limited_calls += 1
            retry_after = rate_limit_result["retry_after"]

            if not wait:
                logger.warning(
                    "Rate limit exceeded, rejecting call",
                    client=self._rate_limit_key,
                    func_name=func_name,
                    retry_after=retry_after,
                )
                raise RateLimitError(
                    f"Rate limit exceeded for {self._rate_limit_key}",
                    retry_after=int(retry_after) if retry_after else None,
                )

            # Wait for token to become available
            logger.info(
                "Rate limit exceeded, waiting for token",
                client=self._rate_limit_key,
                func_name=func_name,
                retry_after=retry_after,
            )

            bucket = self._rate_limiter.get_bucket(self._rate_limit_key)
            token_acquired = bucket.wait_for_token(tokens=1, timeout=timeout)

            if not token_acquired:
                self._stats.failed_calls += 1
                raise RateLimitError(
                    f"Rate limit wait timeout for {self._rate_limit_key}",
                    retry_after=int(timeout),
                )

        # Step 3: Execute with retry through circuit breaker
        # REQ-RATE-004: Retry with exponential backoff
        try:
            result = await self._execute_with_retry(func_name, *args, **kwargs)
            self._stats.successful_calls += 1
            return result
        except Exception as e:
            self._stats.failed_calls += 1
            logger.error(
                "Protected API call failed",
                client=self._rate_limit_key,
                func_name=func_name,
                error=str(e),
            )
            raise

    async def _execute_with_retry(self, func_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with retry logic and circuit breaker protection.

        Args:
            func_name: Name of the method to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the function call

        Raises:
            Exception: Original exception if retries exhausted
        """
        # Get the function from the client
        func = getattr(self._client, func_name)

        # Wrap with circuit breaker
        @self._circuit_breaker.protect
        async def protected_call():
            return await func(*args, **kwargs)

        # Wrap with retry logic
        @async_retry(
            max_attempts=self._retry_config.max_attempts,
            base_delay=self._retry_config.base_delay,
            max_delay=self._retry_config.max_delay,
            exponential_multiplier=self._retry_config.exponential_multiplier,
            jitter=self._retry_config.jitter,
            timeout=self._retry_config.timeout,
        )
        async def call_with_retry():
            return await protected_call()

        return await call_with_retry()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics for the protected client.

        REQ-RATE-002: Track statistics for monitoring.

        Returns:
            Dictionary with statistics including rate limiter and circuit breaker stats
        """
        return {
            "protected_client": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rate_limited_calls": self._stats.rate_limited_calls,
                "circuit_blocked_calls": self._stats.circuit_blocked_calls,
                "last_call_time": self._stats.last_call_time,
            },
            "rate_limiter": self._rate_limiter.get_statistics(),
            "circuit_breaker": {
                "state": self._circuit_breaker.state.value,
                "total_calls": self._circuit_breaker.stats.total_calls,
                "successful_calls": self._circuit_breaker.stats.successful_calls,
                "failed_calls": self._circuit_breaker.stats.failed_calls,
                "consecutive_failures": self._circuit_breaker.stats.consecutive_failures,
            },
        }


__all__ = ["ProtectedAPIClient", "ProtectedClientStats"]
