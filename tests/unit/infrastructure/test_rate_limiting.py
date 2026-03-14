"""
Tests for Rate Limiting infrastructure module.

Test suite following TDD methodology for SPEC-TRADING-009.
"""

from __future__ import annotations

import time

import pytest

from gpt_bitcoin.infrastructure.rate_limiting.rate_limiter import RateLimiter
from gpt_bitcoin.infrastructure.rate_limiting.token_bucket import TokenBucket

# Import from resilience module (consolidated implementation)
from gpt_bitcoin.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)

# Retry decorators are now in resilience module
from gpt_bitcoin.infrastructure.resilience.retry import (
    RetryConfig,
    async_retry,
    sync_retry,
)

# =============================================================================
# TokenBucket Tests
# =============================================================================


class TestTokenBucket:
    """Test TokenBucket rate limiting algorithm."""

    def test_initialization(self):
        """REQ-RATE-001: Test token bucket initialization."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 10  # Starts full

    def test_consume_single_token(self):
        """Test consuming a single token."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        result = bucket.consume(tokens=1)

        assert result is True
        assert bucket.tokens == 9

    def test_consume_multiple_tokens(self):
        """Test consuming multiple tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        result = bucket.consume(tokens=5)

        assert result is True
        assert bucket.tokens == 5

    def test_consume_insufficient_tokens(self):
        """REQ-RATE-003: Test rejection when insufficient tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Use all tokens
        bucket.consume(tokens=10)

        # Try to consume more
        result = bucket.consume(tokens=1)

        assert result is False
        assert bucket.tokens < 1.0  # Should have very small amount from refill

    def test_consume_zero_tokens(self):
        """Test consuming zero tokens (should succeed)."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        result = bucket.consume(tokens=0)

        assert result is True
        assert bucket.tokens == 10

    def test_consume_negative_tokens_raises_error(self):
        """Test that negative tokens raise ValueError."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        with pytest.raises(ValueError, match="tokens must be non-negative"):
            bucket.consume(tokens=-1)

    def test_refill_after_time_passes(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/second

        # Use all tokens
        bucket.consume(tokens=10)
        assert bucket.tokens < 1.0

        # Wait 0.5 seconds - should get 5 tokens back
        time.sleep(0.51)

        # Try to consume - should have 5 tokens available
        result = bucket.consume(tokens=5)

        assert result is True
        assert bucket.tokens < 1.0

    def test_refill_does_not_exceed_capacity(self):
        """Test that refill never exceeds capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)

        # Use half the tokens
        bucket.consume(tokens=5)
        assert bucket.tokens == 5

        # Wait 1 second - should get 5 tokens back to full
        time.sleep(1.01)

        # Try to consume - should have 10 tokens (not 15)
        bucket.consume(tokens=1)
        assert bucket.tokens == 9

    def test_wait_for_token_available_immediately(self):
        """Test wait_for_token when token is available."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        start = time.time()
        result = bucket.wait_for_token(tokens=1, timeout=1.0)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.1  # Should be immediate

    def test_wait_for_token_waits_for_refill(self):
        """REQ-RATE-003: Test wait_for_token waits for refill."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)

        # Use all tokens
        bucket.consume(tokens=10)

        start = time.time()
        result = bucket.wait_for_token(tokens=1, timeout=1.0)
        elapsed = time.time() - start

        assert result is True
        # Should wait about 0.1 seconds for 1 token at 10 tokens/sec
        assert 0.08 < elapsed < 0.2

    def test_wait_for_token_timeout(self):
        """Test wait_for_token times out."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)  # Slow refill

        # Use all tokens
        bucket.consume(tokens=10)

        # Wait for 1 token with short timeout
        start = time.time()
        result = bucket.wait_for_token(tokens=1, timeout=0.05)
        elapsed = time.time() - start

        assert result is False
        assert elapsed >= 0.05  # Should wait full timeout

    def test_get_statistics(self):
        """REQ-RATE-002: Test statistics tracking."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Record some activity
        bucket.consume(tokens=3)
        bucket.consume(tokens=2)

        stats = bucket.get_statistics()

        assert stats["capacity"] == 10
        assert stats["available_tokens"] == 5
        assert stats["consumed_total"] == 5


# =============================================================================
# RateLimiter Tests
# =============================================================================


class TestRateLimiter:
    """Test RateLimiter with multiple buckets."""

    def test_create_bucket_for_key(self):
        """Test creating a bucket for a new key."""
        limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)

        bucket = limiter.get_bucket("api-key-1")

        assert bucket is not None
        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0

    def test_reuse_existing_bucket_for_key(self):
        """Test reusing existing bucket for same key."""
        limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)

        bucket1 = limiter.get_bucket("api-key-1")
        bucket2 = limiter.get_bucket("api-key-1")

        assert bucket1 is bucket2  # Same instance

    def test_different_keys_different_buckets(self):
        """Test different keys get different buckets."""
        limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)

        bucket1 = limiter.get_bucket("api-key-1")
        bucket2 = limiter.get_bucket("api-key-2")

        assert bucket1 is not bucket2

    def test_check_rate_limit_allows_request(self):
        """REQ-RATE-001: Test rate limit check passes."""
        limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)

        result = limiter.check_rate_limit("api-key-1", tokens=5)

        assert result["allowed"] is True
        assert result["tokens_remaining"] == 5

    def test_check_rate_limit_denies_request(self):
        """REQ-RATE-003: Test rate limit check denies."""
        limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)

        # Use all tokens
        limiter.check_rate_limit("api-key-1", tokens=10)

        # Try to consume more
        result = limiter.check_rate_limit("api-key-1", tokens=1)

        assert result["allowed"] is False
        assert result["tokens_remaining"] < 1.0

    def test_get_all_statistics(self):
        """REQ-RATE-002: Test getting statistics for all keys."""
        limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)

        # Create activity on multiple keys
        limiter.check_rate_limit("api-key-1", tokens=5)
        limiter.check_rate_limit("api-key-2", tokens=3)

        stats = limiter.get_statistics()

        assert "api-key-1" in stats
        assert "api-key-2" in stats
        assert stats["api-key-1"]["consumed_total"] == 5
        assert stats["api-key-2"]["consumed_total"] == 3


# =============================================================================
# CircuitBreaker Tests
# =============================================================================


class TestCircuitBreaker:
    """Test CircuitBreaker failure protection using protect decorator."""

    def test_initially_closed_state(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(
            name="test-circuit",
            failure_threshold=3,
            recovery_timeout=60.0,
        )

        assert cb.is_closed is True
        assert cb.is_open is False
        assert cb.is_half_open is False

    def test_successful_call_no_circuit_open(self):
        """Test successful call doesn't open circuit."""
        cb = CircuitBreaker(
            name="test-circuit",
            failure_threshold=3,
            recovery_timeout=60.0,
        )

        @cb.protect
        def success_func():
            return "success"

        result = success_func()

        assert result == "success"
        assert cb.is_closed is True
        assert cb.stats.consecutive_failures == 0

    def test_opens_after_threshold_failures(self):
        """REQ-RATE-006: Test circuit opens after threshold."""
        cb = CircuitBreaker(
            name="test-circuit",
            failure_threshold=3,
            recovery_timeout=60.0,
        )

        @cb.protect
        def failing_func():
            raise ValueError("Test failure")

        # Record failures up to threshold
        for _ in range(3):
            try:
                failing_func()
            except ValueError:
                pass

        # Circuit should now be open
        assert cb.is_open is True
        assert cb.stats.consecutive_failures == 3

    def test_raises_error_when_open(self):
        """REQ-RATE-005: Test raises CircuitBreakerOpenError when OPEN."""
        cb = CircuitBreaker(
            name="test-circuit",
            failure_threshold=2,
            recovery_timeout=60.0,
        )

        @cb.protect
        def failing_func():
            raise ValueError("Test failure")

        # Open the circuit
        for _ in range(2):
            try:
                failing_func()
            except ValueError:
                pass

        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            failing_func()

    def test_stats_tracking(self):
        """REQ-RATE-002: Test statistics are tracked correctly."""
        cb = CircuitBreaker(
            name="test-circuit",
            failure_threshold=3,
            recovery_timeout=60.0,
        )

        call_count = [0]

        @cb.protect
        def mixed_func():
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("Test failure")
            return "success"

        # Record some activity
        mixed_func()  # success
        try:
            mixed_func()  # failure
        except ValueError:
            pass
        mixed_func()  # success

        stats = cb.stats

        assert stats.total_calls == 3
        assert stats.successful_calls == 2
        assert stats.failed_calls == 1
        assert cb.is_closed is True


# =============================================================================
# Retry Decorator Tests (sync_retry and async_retry)
# =============================================================================


class TestRetryDecorators:
    """Test sync_retry and async_retry decorators with exponential backoff."""

    def test_retry_config_initialization(self):
        """Test RetryConfig initialization."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
        )

        assert config.max_attempts == 3
        assert config.base_delay == 0.1
        assert config.max_delay == 1.0
        assert config.exponential_multiplier == 2.0  # Default value

    def test_sync_retry_successful_call_no_retry(self):
        """Test successful call without retry."""

        @sync_retry(max_attempts=3, base_delay=0.1)
        def success_func():
            return "success"

        result = success_func()

        assert result == "success"

    def test_sync_retry_on_failure(self):
        """REQ-RATE-004: Test retry on failure with exponential backoff."""
        attempts = [0]

        @sync_retry(max_attempts=3, base_delay=0.01, max_delay=0.1, jitter=False)
        def failing_func():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        start = time.time()
        result = failing_func()
        elapsed = time.time() - start

        assert result == "success"
        assert attempts[0] == 3
        # Should have delays between retries
        assert elapsed > 0.01  # At least some delay occurred

    def test_sync_retry_max_attempts_exceeded(self):
        """REQ-RATE-010: Test error when max attempts exceeded."""

        @sync_retry(max_attempts=2, base_delay=0.01, jitter=False)
        def always_failing_func():
            raise ConnectionError("Persistent failure")

        # Should raise the original exception after retries
        with pytest.raises(ConnectionError, match="Persistent failure"):
            always_failing_func()

    async def test_async_retry_successful_call_no_retry(self):
        """Test async successful call without retry."""

        @async_retry(max_attempts=3, base_delay=0.1)
        async def success_func():
            return "success"

        result = await success_func()

        assert result == "success"

    async def test_async_retry_on_failure(self):
        """REQ-RATE-004: Test async retry on failure with exponential backoff."""
        attempts = [0]

        @async_retry(max_attempts=3, base_delay=0.01, max_delay=0.1, jitter=False)
        async def failing_func():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        start = time.time()
        result = await failing_func()
        elapsed = time.time() - start

        assert result == "success"
        assert attempts[0] == 3
        assert elapsed > 0.01  # At least some delay occurred

    async def test_async_retry_max_attempts_exceeded(self):
        """REQ-RATE-010: Test async error when max attempts exceeded."""

        @async_retry(max_attempts=2, base_delay=0.01, jitter=False)
        async def always_failing_func():
            raise ConnectionError("Persistent failure")

        # Should raise the original exception after retries
        with pytest.raises(ConnectionError, match="Persistent failure"):
            await always_failing_func()

    def test_retry_config_with_custom_defaults(self):
        """Test RetryConfig with custom default values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_multiplier=3.0,
            jitter=False,
            timeout=30.0,
        )

        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_multiplier == 3.0
        assert config.jitter is False
        assert config.timeout == 30.0
