"""
Unit tests for Circuit Breaker pattern.

Tests cover:
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure threshold triggering
- Recovery timeout behavior
- Decorator and context manager usage
"""

import asyncio
import time

import pytest

from gpt_bitcoin.infrastructure.exceptions import CircuitBreakerOpenError
from gpt_bitcoin.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self):
        """Circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker("test-service")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed
        assert not cb.is_open
        assert not cb.is_half_open

    def test_closed_to_open_after_failure_threshold(self):
        """Circuit should open after reaching failure threshold."""
        cb = CircuitBreaker("test-service", failure_threshold=3)

        # Record failures up to threshold
        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.is_open

    def test_open_to_half_open_after_recovery_timeout(self):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker("test-service", failure_threshold=1, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should allow request (transition to HALF_OPEN)
        assert cb._should_allow_request()
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_after_success_threshold(self):
        """Circuit should close after success threshold in HALF_OPEN."""
        cb = CircuitBreaker(
            "test-service",
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
        )

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.15)
        cb._should_allow_request()  # Transition to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

        # Record successes
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN  # Not yet closed
        cb.record_success()
        assert cb.state == CircuitState.CLOSED  # Now closed

    def test_half_open_to_open_on_failure(self):
        """Circuit should reopen immediately on failure in HALF_OPEN."""
        cb = CircuitBreaker("test-service", failure_threshold=1, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.15)
        cb._should_allow_request()  # Transition to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

        # Failure in HALF_OPEN should reopen
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerDecorator:
    """Test circuit breaker as decorator."""

    @pytest.mark.asyncio
    async def test_async_decorator_allows_calls_when_closed(self):
        """Decorator should allow calls when circuit is closed."""
        cb = CircuitBreaker("test-service")

        @cb.protect
        async def successful_call():
            return "success"

        result = await successful_call()
        assert result == "success"
        assert cb.stats.successful_calls == 1

    @pytest.mark.asyncio
    async def test_async_decorator_blocks_calls_when_open(self):
        """Decorator should block calls when circuit is open."""
        cb = CircuitBreaker("test-service", failure_threshold=1)

        @cb.protect
        async def failing_call():
            raise ValueError("error")

        # Trigger open state
        try:
            await failing_call()
        except ValueError:
            pass

        assert cb.is_open

        # Should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await failing_call()

    @pytest.mark.asyncio
    async def test_async_decorator_records_failures(self):
        """Decorator should record failures."""
        cb = CircuitBreaker("test-service")

        @cb.protect
        async def failing_call():
            raise ValueError("error")

        with pytest.raises(ValueError):
            await failing_call()

        assert cb.stats.failed_calls == 1
        assert cb.stats.consecutive_failures == 1

    def test_sync_decorator_allows_calls_when_closed(self):
        """Sync decorator should work correctly."""
        cb = CircuitBreaker("test-service")

        @cb.protect
        def successful_call():
            return "success"

        result = successful_call()
        assert result == "success"
        assert cb.stats.successful_calls == 1


class TestCircuitBreakerContextManager:
    """Test circuit breaker as context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_success(self):
        """Context manager should record success on normal exit."""
        cb = CircuitBreaker("test-service")

        async with cb:
            pass  # Successful operation

        assert cb.stats.successful_calls == 1

    @pytest.mark.asyncio
    async def test_context_manager_failure(self):
        """Context manager should record failure on exception."""
        cb = CircuitBreaker("test-service")

        with pytest.raises(ValueError):
            async with cb:
                raise ValueError("error")

        assert cb.stats.failed_calls == 1

    @pytest.mark.asyncio
    async def test_context_manager_blocks_when_open(self):
        """Context manager should block when circuit is open."""
        cb = CircuitBreaker("test-service", failure_threshold=1)

        # Open the circuit
        try:
            async with cb:
                raise ValueError("error")
        except ValueError:
            pass

        # Should block
        with pytest.raises(CircuitBreakerOpenError):
            async with cb:
                pass


class TestCircuitBreakerReset:
    """Test circuit breaker reset functionality."""

    def test_reset_clears_state(self):
        """Reset should return circuit to initial state."""
        cb = CircuitBreaker("test-service", failure_threshold=1)

        # Open the circuit
        cb.record_failure()
        assert cb.is_open

        # Reset
        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.stats.consecutive_failures == 0
        assert cb.stats.failed_calls == 0


class TestCircuitBreakerStats:
    """Test circuit breaker statistics."""

    def test_stats_tracking(self):
        """Stats should track calls correctly."""
        cb = CircuitBreaker("test-service")

        cb.record_success()
        cb.record_success()
        cb.record_failure()

        assert cb.stats.total_calls == 3
        assert cb.stats.successful_calls == 2
        assert cb.stats.failed_calls == 1
        assert cb.stats.consecutive_failures == 1

    def test_consecutive_failures_reset_on_success(self):
        """Consecutive failures should reset on success."""
        cb = CircuitBreaker("test-service")

        cb.record_failure()
        cb.record_failure()
        assert cb.stats.consecutive_failures == 2

        cb.record_success()
        assert cb.stats.consecutive_failures == 0


class TestCircuitBreakerHalfOpenLimits:
    """Test HALF_OPEN state call limits - covers lines 161-165, 294."""

    def test_half_open_limits_calls(self):
        """HALF_OPEN state should limit concurrent calls."""
        cb = CircuitBreaker(
            "test-service",
            failure_threshold=1,
            recovery_timeout=0.1,
            half_open_max_calls=2,
        )

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.15)
        cb._should_allow_request()  # Transition to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

        # First call allowed
        assert cb._should_allow_request() is True
        cb._half_open_calls = 1

        # Second call allowed
        assert cb._should_allow_request() is True
        cb._half_open_calls = 2

        # Third call should be blocked
        assert cb._should_allow_request() is False

    def test_sync_call_in_half_open(self):
        """Sync _sync_call should work in HALF_OPEN state."""
        cb = CircuitBreaker(
            "test-service",
            failure_threshold=1,
            recovery_timeout=0.1,
        )

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.15)
        cb._should_allow_request()  # Transition to HALF_OPEN

        # Make successful sync call
        def successful_func():
            return "success"

        result = cb._sync_call(successful_func)
        assert result == "success"

    def test_sync_call_failure_in_half_open(self):
        """Sync _sync_call failure in HALF_OPEN should reopen circuit."""
        cb = CircuitBreaker(
            "test-service",
            failure_threshold=1,
            recovery_timeout=0.1,
        )

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.15)
        cb._should_allow_request()  # Transition to HALF_OPEN

        # Make failing sync call
        def failing_func():
            raise ValueError("error")

        with pytest.raises(ValueError):
            cb._sync_call(failing_func)

        # Should be back to OPEN
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerShouldAllowRequest:
    """Test _should_allow_request edge cases - covers lines 153, 270-273."""

    def test_open_state_without_failure_time(self):
        """OPEN state without last_failure_time should not allow requests."""
        cb = CircuitBreaker("test-service", failure_threshold=1)

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Manually clear last_failure_time to test edge case
        cb._stats.last_failure_time = None

        # Should not allow request (no recovery time to check)
        assert cb._should_allow_request() is False

    def test_unknown_state_returns_false(self):
        """Unknown state should not allow requests."""
        cb = CircuitBreaker("test-service")

        # Force set to an unknown state
        cb._state = "UNKNOWN"  # type: ignore

        # Should return False for unknown state
        assert cb._should_allow_request() is False


class TestCircuitBreakerAsyncCall:
    """Test async _async_call method - covers lines 270-273."""

    @pytest.mark.asyncio
    async def test_async_call_in_half_open(self):
        """Async _async_call should work in HALF_OPEN state."""
        cb = CircuitBreaker(
            "test-service",
            failure_threshold=1,
            recovery_timeout=0.1,
        )

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.15)
        cb._should_allow_request()  # Transition to HALF_OPEN

        # Make successful async call
        async def successful_func():
            return "async_success"

        result = await cb._async_call(successful_func)
        assert result == "async_success"

    @pytest.mark.asyncio
    async def test_async_call_failure_in_half_open(self):
        """Async _async_call failure in HALF_OPEN should reopen circuit."""
        cb = CircuitBreaker(
            "test-service",
            failure_threshold=1,
            recovery_timeout=0.1,
        )

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.15)
        cb._should_allow_request()  # Transition to HALF_OPEN

        # Make failing async call
        async def failing_func():
            raise ValueError("async error")

        with pytest.raises(ValueError):
            await cb._async_call(failing_func)

        # Should be back to OPEN
        assert cb.state == CircuitState.OPEN
