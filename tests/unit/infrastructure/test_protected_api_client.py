"""
Tests for ProtectedAPIClient wrapper.

Test suite following TDD methodology for SPEC-TRADING-009.
Tests the combination of rate limiting, circuit breaker, and retry logic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from gpt_bitcoin.infrastructure.exceptions import CircuitBreakerOpenError, RateLimitError
from gpt_bitcoin.infrastructure.rate_limiting.rate_limiter import RateLimiter
from gpt_bitcoin.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)
from gpt_bitcoin.infrastructure.resilience.retry import RetryConfig

# =============================================================================
# ProtectedAPIClient Tests (RED PHASE - Tests before implementation)
# =============================================================================


class TestProtectedAPIClient:
    """Test ProtectedAPIClient wrapper combining rate limiting, circuit breaker, and retry."""

    async def test_initialization(self):
        """REQ-RATE-001: Test ProtectedAPIClient initialization."""
        # Create mock client
        mock_client = AsyncMock()

        # Create protection components
        rate_limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        circuit_breaker = CircuitBreaker(name="test-api", failure_threshold=3)
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)

        # Import and create ProtectedAPIClient (will fail if not implemented)
        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        assert protected_client is not None
        assert protected_client._client is mock_client
        assert protected_client._rate_limiter is rate_limiter
        assert protected_client._circuit_breaker is circuit_breaker
        assert protected_client._retry_config is retry_config

    async def test_successful_call_passes_through(self):
        """REQ-RATE-001: Test successful API call passes through all protections."""
        # Create mock client with successful method
        mock_client = AsyncMock()
        mock_client.some_method = AsyncMock(return_value="success")

        # Create protection components
        rate_limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        circuit_breaker = CircuitBreaker(name="test-api", failure_threshold=3)
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        # Call the protected method
        result = await protected_client.call("some_method", arg1="value1")

        assert result == "success"
        mock_client.some_method.assert_called_once_with(arg1="value1")

    async def test_rate_limit_rejected(self):
        """REQ-RATE-003: Test rate limit rejection."""
        # Create mock client
        mock_client = AsyncMock()
        mock_client.some_method = AsyncMock(return_value="success")

        # Create rate limiter with very low capacity
        rate_limiter = RateLimiter(default_capacity=1, default_refill_rate=0.1)
        circuit_breaker = CircuitBreaker(name="test-api", failure_threshold=3)
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        # First call should consume the only token
        await protected_client.call("some_method")

        # Second call should be rate limited
        with pytest.raises(RateLimitError):
            await protected_client.call("some_method", wait=False)

    async def test_circuit_open_rejects_call(self):
        """REQ-RATE-005: Test circuit open rejects call immediately."""
        # Create mock client that always fails
        mock_client = AsyncMock()
        mock_client.failing_method = AsyncMock(side_effect=ConnectionError("API down"))

        # Create protection components
        rate_limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        circuit_breaker = CircuitBreaker(
            name="test-api", failure_threshold=2, recovery_timeout=60.0
        )
        retry_config = RetryConfig(max_attempts=1, base_delay=0.01)  # Fail fast

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        # Trigger failures to open circuit
        for _ in range(2):
            try:
                await protected_client.call("failing_method")
            except ConnectionError:
                pass

        # Circuit should now be open
        assert circuit_breaker.is_open

        # Next call should raise CircuitBreakerOpenError immediately
        with pytest.raises(CircuitBreakerOpenError):
            await protected_client.call("failing_method")

        # Verify the underlying method was NOT called (circuit blocked it)
        assert mock_client.failing_method.call_count == 2

    async def test_retry_on_failure(self):
        """REQ-RATE-004: Test retry with exponential backoff."""
        # Create mock client that fails then succeeds
        mock_client = AsyncMock()
        call_count = [0]

        async def flaky_method(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        mock_client.flaky_method = flaky_method

        # Create protection components
        rate_limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        circuit_breaker = CircuitBreaker(
            name="test-api", failure_threshold=5, recovery_timeout=60.0
        )
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        # Call should succeed after retries
        result = await protected_client.call("flaky_method")

        assert result == "success"
        assert call_count[0] == 3  # Failed twice, succeeded on third try

    async def test_retry_exhaustion_raises_error(self):
        """REQ-RATE-010: Test error raised after max retries."""
        # Create mock client that always fails
        mock_client = AsyncMock()
        mock_client.failing_method = AsyncMock(side_effect=ConnectionError("API down"))

        # Create protection components with low retry limit
        rate_limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        circuit_breaker = CircuitBreaker(
            name="test-api", failure_threshold=5, recovery_timeout=60.0
        )
        retry_config = RetryConfig(max_attempts=2, base_delay=0.01, jitter=False)

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        # Should raise original error after retries exhausted
        with pytest.raises(ConnectionError, match="API down"):
            await protected_client.call("failing_method")

        # Verify retries were attempted
        assert mock_client.failing_method.call_count == 2

    async def test_call_with_args_and_kwargs(self):
        """Test that args and kwargs are passed through correctly."""
        # Create mock client
        mock_client = AsyncMock()
        mock_client.method_with_args = AsyncMock(return_value="result")

        # Create protection components
        rate_limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        circuit_breaker = CircuitBreaker(name="test-api", failure_threshold=3)
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        # Call with both args and kwargs
        result = await protected_client.call(
            "method_with_args", "positional_arg", keyword_arg="value"
        )

        assert result == "result"
        mock_client.method_with_args.assert_called_once_with("positional_arg", keyword_arg="value")

    async def test_statistics_tracking(self):
        """REQ-RATE-002: Test statistics are tracked."""
        # Create mock client
        mock_client = AsyncMock()
        mock_client.test_method = AsyncMock(return_value="success")

        # Create protection components
        rate_limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        circuit_breaker = CircuitBreaker(name="test-api", failure_threshold=3)
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        # Make some calls
        await protected_client.call("test_method")
        await protected_client.call("test_method")

        # Get statistics
        stats = protected_client.get_statistics()

        # Verify statistics are tracked
        assert "rate_limiter" in stats
        assert "circuit_breaker" in stats
        assert "protected_client" in stats
        # Rate limiter stats use "consumed_total" not "total_requests"
        assert stats["rate_limiter"][mock_client.__class__.__name__]["consumed_total"] >= 2
        assert stats["circuit_breaker"]["total_calls"] >= 2
        assert stats["protected_client"]["total_calls"] == 2
        assert stats["protected_client"]["successful_calls"] == 2

    async def test_wait_for_rate_limit(self):
        """REQ-RATE-003: Test wait=True waits for rate limit token."""
        # Create mock client
        mock_client = AsyncMock()
        mock_client.test_method = AsyncMock(return_value="success")

        # Create rate limiter with low capacity and slow refill
        rate_limiter = RateLimiter(default_capacity=1, default_refill_rate=10.0)  # Fast refill
        circuit_breaker = CircuitBreaker(name="test-api", failure_threshold=3)
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
        )

        # First call consumes the only token
        await protected_client.call("test_method", wait=False)

        # Second call with wait=True should wait for refill
        result = await protected_client.call("test_method", wait=True, timeout=0.5)

        assert result == "success"
        assert mock_client.test_method.call_count == 2

    async def test_rate_limit_with_custom_key(self):
        """Test rate limiting with custom API key."""
        # Create mock client
        mock_client = AsyncMock()
        mock_client.test_method = AsyncMock(return_value="success")

        # Create protection components
        rate_limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        circuit_breaker = CircuitBreaker(name="test-api", failure_threshold=3)
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)

        from gpt_bitcoin.infrastructure.rate_limiting.protected_client import (
            ProtectedAPIClient,
        )

        protected_client = ProtectedAPIClient(
            client=mock_client,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_config=retry_config,
            rate_limit_key="custom-api-key",
        )

        # Call with custom key
        await protected_client.call("test_method")

        # Verify the custom key was used in rate limiter
        stats = rate_limiter.get_statistics()
        assert "custom-api-key" in stats
