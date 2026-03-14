"""
Unit tests for retry utilities.

Tests cover:
- RetryConfig dataclass
- sync_retry decorator
- async_retry decorator
- Exception handling
"""

import pytest

from gpt_bitcoin.infrastructure.resilience.retry import (
    RetryConfig,
    async_retry,
    sync_retry,
)


class TestRetryConfig:
    """Test RetryConfig dataclass."""

    def test_default_values(self):
        """RetryConfig should have sensible defaults."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_multiplier == 2.0
        assert config.jitter is True
        assert config.timeout is None
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions

    def test_custom_values(self):
        """RetryConfig should accept custom values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_multiplier=3.0,
            jitter=False,
            timeout=120.0,
            retryable_exceptions=(ValueError, KeyError),
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_multiplier == 3.0
        assert config.jitter is False
        assert config.timeout == 120.0
        assert config.retryable_exceptions == (ValueError, KeyError)


class TestSyncRetry:
    """Test sync_retry decorator."""

    def test_success_without_retry(self):
        """sync_retry should not retry on success."""
        call_count = 0

        @sync_retry(max_attempts=3, jitter=False)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_non_retryable_exception_not_retried(self):
        """sync_retry should not retry non-retryable exceptions."""
        call_count = 0

        @sync_retry(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,),
        )
        def raise_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError, match="Not retryable"):
            raise_value_error()

        # Should not retry on ValueError
        assert call_count == 1

    def test_preserves_function_metadata(self):
        """sync_retry should preserve function name and docstring."""

        @sync_retry()
        def documented_function():
            """This is a documented function."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function."

    def test_passes_arguments_correctly(self):
        """sync_retry should pass arguments to decorated function."""

        @sync_retry(max_attempts=1)
        def add_numbers(a, b, c=0):
            return a + b + c

        assert add_numbers(1, 2) == 3
        assert add_numbers(1, 2, c=3) == 6

    def test_with_config_object(self):
        """sync_retry should accept RetryConfig object."""
        call_count = 0
        config = RetryConfig(
            max_attempts=1,
            base_delay=0.01,
            jitter=False,
        )

        @sync_retry(config=config)
        def simple_func():
            nonlocal call_count
            call_count += 1
            return "done"

        result = simple_func()
        assert result == "done"
        assert call_count == 1


class TestAsyncRetry:
    """Test async_retry decorator."""

    @pytest.mark.asyncio
    async def test_success_without_retry(self):
        """async_retry should not retry on success."""
        call_count = 0

        @async_retry(max_attempts=3, jitter=False)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_non_retryable_exception_not_retried(self):
        """async_retry should not retry non-retryable exceptions."""
        call_count = 0

        @async_retry(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,),
        )
        async def raise_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError, match="Not retryable"):
            await raise_value_error()

        # Should not retry on ValueError
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        """async_retry should preserve function name and docstring."""

        @async_retry()
        async def documented_function():
            """This is a documented async function."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented async function."

    @pytest.mark.asyncio
    async def test_passes_arguments_correctly(self):
        """async_retry should pass arguments to decorated function."""

        @async_retry(max_attempts=1)
        async def add_numbers(a, b, c=0):
            return a + b + c

        assert await add_numbers(1, 2) == 3
        assert await add_numbers(1, 2, c=3) == 6

    @pytest.mark.asyncio
    async def test_with_config_object(self):
        """async_retry should accept RetryConfig object."""
        call_count = 0
        config = RetryConfig(
            max_attempts=1,
            base_delay=0.01,
            jitter=False,
        )

        @async_retry(config=config)
        async def simple_func():
            nonlocal call_count
            call_count += 1
            return "done"

        result = await simple_func()
        assert result == "done"
        assert call_count == 1


class TestSyncRetryWithException:
    """Test sync_retry exception handling."""

    def test_non_retryable_not_retried_multiple_times(self):
        """Non-retryable exceptions should not be retried."""
        call_count = 0

        @sync_retry(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(TimeoutError,),
        )
        def raises_non_retryable():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Not retryable")

        with pytest.raises(ConnectionError):
            raises_non_retryable()

        # Should only be called once since ConnectionError is not retryable
        assert call_count == 1


class TestAsyncRetryWithException:
    """Test async_retry exception handling."""

    @pytest.mark.asyncio
    async def test_non_retryable_not_retried_multiple_times(self):
        """Non-retryable exceptions should not be retried."""
        call_count = 0

        @async_retry(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(TimeoutError,),
        )
        async def raises_non_retryable():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Not retryable")

        with pytest.raises(ConnectionError):
            await raises_non_retryable()

        # Should only be called once since ConnectionError is not retryable
        assert call_count == 1
